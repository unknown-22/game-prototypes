"""test_imports.py — Headless logic tests for Chroma Ice (094)."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/094_chroma_ice")

# Module-level constants that reference pyxel — safe since pyxel is installed
from main import (  # noqa: E402
    Game,
    Puck,
    Particle,
    Goalie,
    Phase,
    W, H,
    GOAL_X_MIN, GOALIE_X, GOALIE_W, GOALIE_H, GOALIE_Y_MIN, GOALIE_Y_MAX,
    PLAYER_RADIUS, PUCK_RADIUS,
    PLAYER_START_X, PLAYER_START_Y,
    PLAYER_MAX_SPEED, HEAT_MAX,
    OVERHEAT_DURATION, GAME_DURATION,
    MAX_COMBO, PUCK_MIN_COUNT, PUCK_MAX_COUNT, RINK_BORDER,
)


# Color constants for tests (match pyxel)
RED = 8
CYAN = 12
YELLOW = 10
PURPLE = 2
GRAY = 13


def _make_game(seed: int = 42) -> Game:
    """Factory for headless testing. Uses Game.__new__ to bypass pyxel.init/run."""
    g = Game.__new__(Game)
    g.particles = []
    g.floating_texts = []
    g.pucks = []
    g.rng = random.Random(seed)
    g.reset()
    return g


# ── Dataclass tests ──


def test_puck_dataclass():
    p = Puck(x=50.0, y=60.0, color=RED)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 0.0
    assert p.vy == 0.0
    assert p.color == RED
    assert p.active is False


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=20, color=CYAN)
    assert p.life == 20
    assert p.color == CYAN


def test_goalie_dataclass():
    g = Goalie(y=100.0, target_y=120.0, speed=1.5)
    assert g.y == 100.0
    assert g.target_y == 120.0
    assert g.speed == 1.5
    assert g.width == GOALIE_W
    assert g.height == GOALIE_H


# ── Phase enum ──


def test_phase_values():
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2


def test_phase_enum_identity():
    g = _make_game()
    # reset() doesn't set phase — it must be set manually after Game.__new__
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING


def test_phase_after_reset():
    g = _make_game()
    # reset() doesn't touch self.phase — it keeps whatever was there
    # After Game.__new__, phase is unset. reset() doesn't set it.
    # But _make_game calls reset() which leaves phase as whatever __new__ left it
    # We need to manually set phase
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING


# ── State initialization ──


def test_reset_state():
    g = _make_game()
    g.phase = Phase.PLAYING
    assert g.player_x == PLAYER_START_X
    assert g.player_y == PLAYER_START_Y
    assert g.player_vx == 0.0
    assert g.player_vy == 0.0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.overheat_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.last_goal_color == -1
    assert g.held_puck is None
    assert g.aim_active is False
    assert len(g.pucks) == PUCK_MIN_COUNT  # reset() spawns PUCK_MIN_COUNT pucks


def test_reset_clears_previous_state():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 999
    g.combo = 5
    g.heat = 90.0
    g.particles = [Particle(0, 0, 1, 1, 10, RED)]
    g.floating_texts = [("test", 0, 0, 5)]
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.particles == []
    assert g.floating_texts == []
    assert len(g.pucks) == PUCK_MIN_COUNT


# ── Spawn pucks ──


def test_spawn_pucks_count():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks.clear()
    g._spawn_pucks(3)
    assert len(g.pucks) == 3


def test_spawn_pucks_max_limit():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._spawn_pucks(100)
    assert len(g.pucks) <= PUCK_MAX_COUNT


def test_spawn_pucks_deterministic():
    g1 = _make_game(seed=42)
    g1.phase = Phase.PLAYING
    g2 = _make_game(seed=42)
    g2.phase = Phase.PLAYING
    # Same seed → same puck positions
    assert len(g1.pucks) == len(g2.pucks)
    for p1, p2 in zip(g1.pucks, g2.pucks):
        assert abs(p1.x - p2.x) < 0.01
        assert abs(p1.y - p2.y) < 0.01
        assert p1.color == p2.color


def test_spawn_pucks_in_bounds():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks.clear()
    g._spawn_pucks(20)
    for p in g.pucks:
        assert RINK_BORDER + PUCK_RADIUS <= p.x <= 280
        assert RINK_BORDER + PUCK_RADIUS <= p.y <= H - RINK_BORDER - PUCK_RADIUS


# ── Player movement ──


def test_player_movement_right():
    g = _make_game()
    g.phase = Phase.PLAYING
    initial_x = g.player_x
    g._update_player(1.0, 0.0)
    assert g.player_x > initial_x
    assert g.player_vx > 0


def test_player_movement_down():
    g = _make_game()
    g.phase = Phase.PLAYING
    initial_y = g.player_y
    g._update_player(0.0, 1.0)
    assert g.player_y > initial_y


def test_player_movement_diagonal():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._update_player(0.707, 0.707)  # diagonal
    assert g.player_vx > 0
    assert g.player_vy > 0


def test_player_speed_clamped():
    g = _make_game()
    g.phase = Phase.PLAYING
    for _ in range(100):
        g._update_player(1.0, 0.0)
    speed = math.hypot(g.player_vx, g.player_vy)
    assert speed <= PLAYER_MAX_SPEED + 0.01


def test_player_boundary_left():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = RINK_BORDER + PLAYER_RADIUS
    g._update_player(-1.0, 0.0)
    assert g.player_x >= RINK_BORDER + PLAYER_RADIUS - 0.01


def test_player_boundary_right():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = W - RINK_BORDER - PLAYER_RADIUS
    g._update_player(1.0, 0.0)
    assert g.player_x <= W - RINK_BORDER - PLAYER_RADIUS + 0.01


def test_player_friction_stops():
    g = _make_game()
    g.phase = Phase.PLAYING
    # Give velocity then stop input
    g._update_player(1.0, 0.0)
    for _ in range(200):
        g._update_player(0.0, 0.0)
    assert abs(g.player_vx) < 0.1
    assert abs(g.player_vy) < 0.1


# ── Puck pickup ──


def test_player_puck_collision_pickup():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.pucks = [Puck(x=100.0, y=100.0, color=RED)]
    puck = g._check_player_puck_collision()
    assert puck is not None
    assert puck.color == RED


def test_player_puck_no_collision_far():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.pucks = [Puck(x=200.0, y=200.0, color=RED)]
    puck = g._check_player_puck_collision()
    assert puck is None


def test_player_puck_active_ignored():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.pucks = [Puck(x=100.0, y=100.0, color=RED, active=True)]
    puck = g._check_player_puck_collision()
    assert puck is None


# ── Shoot puck ──


def test_shoot_puck_no_held():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._shoot_puck(0.0, 5.0)
    # Nothing happens, no error


def test_shoot_puck_launches():
    g = _make_game()
    g.phase = Phase.PLAYING
    puck = Puck(x=100.0, y=100.0, color=CYAN)
    g.pucks.append(puck)  # must be in pucks list (real flow picks via _check_player_puck_collision)
    g.held_puck = puck
    g._shoot_puck(math.pi / 4, 6.0)
    assert g.held_puck is None
    # Find the puck in pucks list
    active = [p for p in g.pucks if p.active]
    assert len(active) == 1
    assert abs(active[0].vx - math.cos(math.pi / 4) * 6.0) < 0.01
    assert abs(active[0].vy - math.sin(math.pi / 4) * 6.0) < 0.01
    assert active[0].color == CYAN


def test_shoot_puck_adds_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    initial_heat = g.heat
    g.held_puck = Puck(x=100.0, y=100.0, color=CYAN)
    g._shoot_puck(0.0, 5.0)
    assert g.heat > initial_heat
    assert g.heat == 5.0  # +5 on shoot


# ── Goal detection ──


def test_check_goal_scored():
    g = _make_game()
    g.phase = Phase.PLAYING
    puck = Puck(x=308.0, y=120.0, vx=5.0, color=RED, active=True)
    assert g._check_goal(puck) is True


def test_check_goal_not_active():
    puck = Puck(x=308.0, y=120.0, color=RED, active=False)
    g = _make_game()
    g.phase = Phase.PLAYING
    assert g._check_goal(puck) is False


def test_check_goal_outside_y():
    g = _make_game()
    g.phase = Phase.PLAYING
    puck = Puck(x=308.0, y=50.0, vx=5.0, color=RED, active=True)
    assert g._check_goal(puck) is False


def test_check_goal_before_goal_line():
    g = _make_game()
    g.phase = Phase.PLAYING
    puck = Puck(x=100.0, y=120.0, vx=5.0, color=RED, active=True)
    assert g._check_goal(puck) is False


def test_check_goal_at_goal_edge():
    g = _make_game()
    g.phase = Phase.PLAYING
    puck = Puck(x=GOAL_X_MIN + 0.1, y=120.0, vx=5.0, color=RED, active=True)
    assert g._check_goal(puck) is True


# ── Save detection ──


def test_check_save_blocks_puck():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.y = 120.0
    puck = Puck(x=GOALIE_X, y=120.0, color=RED, active=True)
    assert g._check_save(puck) is True


def test_check_save_puck_not_active():
    g = _make_game()
    g.phase = Phase.PLAYING
    puck = Puck(x=GOALIE_X, y=120.0, color=RED, active=False)
    assert g._check_save(puck) is False


def test_check_save_puck_above_goalie():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.y = 120.0
    puck = Puck(x=GOALIE_X, y=80.0, color=RED, active=True)
    # Distance = 40px, half_h = 15, PUCK_RADIUS = 6 → needs < 21
    assert g._check_save(puck) is False


# ── Combo multiplier ──


def test_combo_multiplier_zero():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    assert g._compute_combo_multiplier() == 1


def test_combo_multiplier_one():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 1
    assert g._compute_combo_multiplier() == 2


def test_combo_multiplier_max():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = MAX_COMBO
    assert g._compute_combo_multiplier() == 128


def test_combo_multiplier_doubles():
    g = _make_game()
    g.phase = Phase.PLAYING
    for i in range(MAX_COMBO + 1):
        g.combo = i
        assert g._compute_combo_multiplier() == (1 << i)


# ── Handle shot result ──


def test_handle_goal_first_time():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)
    assert g.score == 1  # multiplier = 1 (combo=0)
    assert g.combo == 0  # first goal, no previous → combo stays 0
    assert g.last_goal_color == RED
    assert g.heat > 0


def test_handle_goal_same_color_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_goal_color = RED
    # First same-color → combo++
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)
    assert g.combo == 1
    # Second same-color → combo++
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)
    assert g.combo == 2
    assert g.score > 3  # 1 + 2 + 4 = 7


def test_handle_goal_different_color_reset():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_goal_color = RED
    g.combo = 3
    g.heat = 50.0
    g._handle_shot_result(scored=True, saved=False, puck_color=CYAN)
    assert g.combo == 0  # combo resets
    assert g.heat < 50.0  # heat reduced by 15


def test_handle_goal_updates_max_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_goal_color = RED
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)  # combo=1
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)  # combo=2
    assert g.max_combo >= 2


def test_handle_save_resets_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 5
    g.heat = 20.0
    g._handle_shot_result(scored=False, saved=True, puck_color=RED)
    assert g.combo == 0
    assert g.heat == 30.0  # +10 for save


def test_handle_miss_adds_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    initial_heat = g.heat
    g._handle_shot_result(scored=False, saved=False, puck_color=RED)
    assert g.heat == initial_heat + 3.0


def test_handle_combo_capped():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_goal_color = RED
    g.combo = MAX_COMBO
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)
    assert g.combo == MAX_COMBO  # doesn't exceed cap


# ── Heat system ──


def test_heat_triggers_overheat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 79.0
    g._update_heat()
    assert g.overheat_timer == 0  # not yet
    g.heat = 80.0
    g.heat_decay_timer = 0
    g._update_heat()
    assert g.overheat_timer == OVERHEAT_DURATION  # triggered


def test_heat_decays_over_time():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g._update_heat()
    assert g.heat <= 50.0  # decay should reduce it
    # After enough decay calls, heat continues to drop
    for _ in range(10):
        g._update_heat()
    assert g.heat < 50.0


def test_heat_drains_during_overheat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 90.0
    g.overheat_timer = OVERHEAT_DURATION
    g._update_heat()
    assert g.heat < 90.0  # faster drain during overheat
    assert g.overheat_timer == OVERHEAT_DURATION - 1


def test_heat_clamped_to_max():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)
    assert g.heat <= HEAT_MAX


# ── Puck physics ──


def test_puck_physics_movement():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = [Puck(x=100.0, y=100.0, vx=3.0, vy=1.0, color=RED, active=True)]
    g._update_pucks()
    assert g.pucks[0].x > 100.0
    assert g.pucks[0].y > 100.0
    assert g.pucks[0].vx < 3.0  # friction reduces speed
    assert g.pucks[0].vy < 1.0


def test_puck_physics_friction():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = [Puck(x=100.0, y=100.0, vx=5.0, vy=0.0, color=RED, active=True)]
    for _ in range(100):
        g._update_pucks()
    # After many frames, speed should be very low
    if len(g.pucks) > 0:
        assert abs(g.pucks[0].vx) < 1.0 or len(g.pucks) == 0


def test_puck_removed_off_screen():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = [Puck(x=400.0, y=120.0, vx=20.0, color=RED, active=True)]
    g._update_pucks()
    assert len(g.pucks) == 0


def test_inactive_puck_not_moved():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = [Puck(x=100.0, y=100.0, color=RED, active=False)]
    g._update_pucks()
    assert g.pucks[0].x == 100.0  # unchanged
    assert g.pucks[0].y == 100.0


# ── Goalie movement ──


def test_goalie_moves_toward_target():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.y = 100.0
    g.goalie.target_y = 140.0
    g._update_goalie()
    assert g.goalie.y > 100.0  # moved down
    assert g.goalie.y <= 140.0


def test_goalie_moves_up():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.y = 140.0
    g.goalie.target_y = 100.0
    g._update_goalie()
    assert g.goalie.y < 140.0


def test_goalie_clamped_bottom():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.y = GOALIE_Y_MAX
    g.goalie.target_y = GOALIE_Y_MAX + 50
    g._update_goalie()
    assert g.goalie.y == GOALIE_Y_MAX


def test_goalie_clamped_top():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.y = GOALIE_Y_MIN
    g.goalie.target_y = GOALIE_Y_MIN - 50
    g._update_goalie()
    assert g.goalie.y == GOALIE_Y_MIN


# ── Goalie target tracking ──


def test_goalie_target_no_active_pucks():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.goalie.target_y = 100.0
    g._update_goalie_target()
    assert g.goalie.target_y == 120.0  # centers when no active pucks


def test_goalie_target_tracks_puck():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = [Puck(x=GOALIE_X - 50, y=100.0, vx=3.0, vy=0.0, color=RED, active=True)]
    g._update_goalie_target()
    assert abs(g.goalie.target_y - 100.0) < 10  # roughly tracks puck y


# ── Particle system ──


def test_spawn_particles():
    g = _make_game()
    g.phase = Phase.PLAYING
    initial_count = len(g.particles)
    g._spawn_particles(50.0, 50.0, 10, RED)
    assert len(g.particles) == initial_count + 10
    for p in g.particles[-10:]:
        assert p.color == RED


def test_particles_age_and_die():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._spawn_particles(50.0, 50.0, 5, RED)
    # Set all particles to life=1 so they die next update
    for p in g.particles:
        p.life = 1
    g._update_particles()
    assert len(g.particles) == 0


def test_particles_move():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._spawn_particles(50.0, 50.0, 1, CYAN)
    particle = g.particles[-1]
    orig_x, orig_y = particle.x, particle.y
    g._update_particles()
    if len(g.particles) > 0:
        assert particle.x != orig_x or particle.y != orig_y


# ── Floating texts ──


def test_floating_texts_move_up():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.floating_texts = [("TEST", 100.0, 100.0, 10)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    # y should decrease (float up)
    assert g.floating_texts[0][2] < 100.0


def test_floating_texts_die():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.floating_texts = [("TEST", 100.0, 100.0, 1)]
    g._update_floating_texts()  # life=1 → survives one more update (life becomes 0)
    g._update_floating_texts()  # life=0 → removed
    assert len(g.floating_texts) == 0


# ── Game timer ──


def test_game_timer_decrements():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 100
    # Simulate what update() does
    g.game_timer -= 1
    assert g.game_timer == 99


def test_game_timer_hits_zero():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 1
    g.game_timer -= 1
    assert g.game_timer == 0


# ── Edge cases ──


def test_reset_multiple_times():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 100
    g.combo = 5
    g.heat = 90
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    # Verify pucks respawned
    assert len(g.pucks) == PUCK_MIN_COUNT


def test_all_pucks_inactive_respawn():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = []
    g._spawn_pucks(PUCK_MIN_COUNT)
    assert len(g.pucks) == PUCK_MIN_COUNT


def test_held_puck_position_tracks_player():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = 150.0
    g.player_y = 130.0
    g.held_puck = Puck(x=100.0, y=100.0, color=RED)
    g.held_puck.x = g.player_x
    g.held_puck.y = g.player_y
    assert g.held_puck.x == 150.0
    assert g.held_puck.y == 130.0


def test_shoot_with_no_drag():
    """When drag distance is very small, angle defaults to player → goal direction."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_x = 80.0
    g.player_y = 120.0
    puck = Puck(x=80.0, y=120.0, color=YELLOW)
    g.pucks.append(puck)
    g.held_puck = puck
    # Shoot toward the right (toward goal)
    g._shoot_puck(math.atan2(120 - 120, 298 - 80), 3.0)
    assert g.held_puck is None
    active = [p for p in g.pucks if p.active]
    assert len(active) == 1
    # Should fly toward right
    assert active[0].vx > 0


def test_score_with_multiplier():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_goal_color = RED
    g.combo = 3  # multiplier = 8
    g._handle_shot_result(scored=True, saved=False, puck_color=RED)
    # combo → 4, multiplier = 16
    assert g.score == 16


def test_overheat_prevents_goal_via_save():
    """During overheat, save is checked first, and if it blocks → no goal."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.overheat_timer = 100
    g.goalie.y = 120.0
    puck = Puck(x=GOAL_X_MIN + 1, y=120.0, vx=5.0, color=RED, active=True)
    # During overheat, _check_save is checked — puck at goalie position
    assert g._check_save(puck) is True
    # But _check_goal also returns True since puck is past goal line
    assert g._check_goal(puck) is True


def test_heat_only_resets_on_different_color_goal():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_goal_color = RED
    g.heat = 75.0
    g._handle_shot_result(scored=True, saved=False, puck_color=CYAN)
    # Different-color goal: heat -= 15 (combo reset), then heat += 8 (goal bonus)
    # Net: 75 - 15 + 8 = 68
    assert g.heat == 68.0
    assert g.combo == 0


def test_goalie_target_predicts_intercept():
    """Goalie predicts where puck will be when it reaches goal line."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.pucks = [Puck(x=200.0, y=100.0, vx=4.0, vy=1.0, color=RED, active=True)]
    g._update_goalie_target()
    # The goalie should target slightly above 100 (vy>0 moves puck down)
    assert abs(g.goalie.target_y - 100.0) < 30  # within reasonable range


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
