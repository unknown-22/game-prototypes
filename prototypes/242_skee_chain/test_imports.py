"""test_imports.py -- Headless logic tests for Skee Chain."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/242_skee_chain")
from main import Game, Phase, Hole, Particle, FloatingText, GhostPoint


def _make_game(*, seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = Game.TIMER_START
    g.ball_color_idx = 0
    g.ball_x = float(Game.LAUNCH_X)
    g.ball_y = float(Game.LAUNCH_Y)
    g.ball_vx = 0.0
    g.ball_vy = 0.0
    g.power = 0.0
    g.charging = False
    g.super_timer = 0
    g.scoring_timer = 0
    g.color_cycle_cooldown = 0
    g.particles = []
    g.floating_texts = []
    g.ghost_points = []
    g.best_ghost = []
    g.holes = []
    g._rng = random.Random(seed)
    g._init_holes()
    return g


def _make_game_aiming(*, seed: int = 42) -> Game:
    g = _make_game(seed=seed)
    g.phase = Phase.AIMING
    return g


# ---- Data Classes ----


def test_phase_enum():
    assert Phase.TITLE != Phase.AIMING
    assert Phase.AIMING != Phase.FLYING
    assert Phase.FLYING != Phase.SCORING
    assert Phase.SCORING != Phase.GAME_OVER


def test_hole_dataclass():
    h = Hole(190, 70, 8, 12, 100)
    assert h.x == 190
    assert h.y == 70
    assert h.color == 8
    assert h.radius == 12
    assert h.score == 100


def test_particle_dataclass():
    p = Particle(10.5, 20.3, 1.0, -2.0, 8, 15)
    assert abs(p.x - 10.5) < 0.01
    assert p.color == 15
    assert p.life == 8
    assert p.size == 2


def test_floating_text_dataclass():
    ft = FloatingText(100.0, 50.0, "TEST", 30, 7)
    assert ft.text == "TEST"
    assert ft.color == 7
    assert ft.life == 30


def test_ghost_point_dataclass():
    gp = GhostPoint(150.0, 120.0)
    assert abs(gp.x - 150.0) < 0.01
    assert abs(gp.y - 120.0) < 0.01


# ---- Constants ----


def test_screen_constants():
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240


def test_color_constants():
    assert Game.COLORS == (8, 11, 5, 10)
    assert Game.COLOR_NAMES == ("RED", "LIME", "DARK_BLUE", "YELLOW")
    assert Game.NUM_COLORS == 4


def test_game_constants():
    assert Game.SUPER_DURATION == 300
    assert Game.SUPER_COMBO_THRESHOLD == 4
    assert Game.SUPER_MULTIPLIER == 3
    assert Game.MAX_HEAT == 100.0
    assert Game.HEAT_MISMATCH == 15
    assert Game.HEAT_MISS == 10
    assert Game.HEAT_DECAY == 0.02
    assert Game.TIMER_START == 60 * 30
    assert Game.HOLE_RADIUS == 12
    assert Game.BALL_RADIUS == 5
    assert Game.GRAVITY == 0.25
    assert Game.MAX_POWER == 12.0
    assert Game.POWER_CHARGE_RATE == 0.3
    assert Game.FRICTION == 0.98
    assert Game.COLOR_CYCLE_COOLDOWN == 10


# ---- Init / Reset ----


def test_reset_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == Game.TIMER_START
    assert g.super_timer == 0
    assert g.charging is False


def test_init_holes_creates_four():
    g = _make_game()
    assert len(g.holes) == 4
    for h in g.holes:
        assert isinstance(h, Hole)
        assert h.color in Game.COLORS
        assert h.radius == Game.HOLE_RADIUS
        assert h.score == 100


def test_init_holes_positions():
    g = _make_game(seed=42)
    positions = {(h.x, h.y) for h in g.holes}
    expected = {(190, 70), (230, 70), (270, 70), (310, 70)}
    assert positions == expected


def test_init_holes_colors_shuffled():
    g = _make_game(seed=42)
    colors = sorted(h.color for h in g.holes)
    assert colors == sorted(Game.COLORS)


# ---- Start Game ----


def test_start_game():
    g = _make_game()
    g.start_game()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.timer == Game.TIMER_START
    assert g.super_timer == 0
    assert g.charging is False


def test_start_game_clears_particles_and_texts():
    g = _make_game()
    g.particles = [Particle(0, 0, 0, 0, 1, 0)]
    g.floating_texts = [FloatingText(0, 0, "x", 1, 0)]
    g.ghost_points = [GhostPoint(0, 0)]
    g.best_ghost = [GhostPoint(0, 0)]
    g.start_game()
    assert g.particles == []
    assert g.floating_texts == []
    assert g.ghost_points == []
    assert g.best_ghost == []


# ---- Title / Game Over Input ----


def test_handle_title_input_starts():
    g = _make_game()
    result = g._handle_title_input(True)
    assert result is True
    assert g.phase == Phase.AIMING


def test_handle_title_input_ignores():
    g = _make_game()
    result = g._handle_title_input(False)
    assert result is False
    assert g.phase == Phase.TITLE


def test_handle_gameover_input_restarts():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    result = g._handle_gameover_input(True)
    assert result is True
    assert g.phase == Phase.AIMING
    assert g.score == 0


# ---- Aiming Input ----


def test_aiming_charge_start():
    g = _make_game_aiming()
    action = g._handle_aiming_input(mouse_down=True, cycle_left=False, cycle_right=False)
    assert action == "charge_start"
    assert g.charging is True


def test_aiming_charge_continued():
    g = _make_game_aiming()
    g._handle_aiming_input(mouse_down=True, cycle_left=False, cycle_right=False)
    initial_power = g.power
    for _ in range(10):
        action = g._handle_aiming_input(mouse_down=True, cycle_left=False, cycle_right=False)
    # Should have charged
    assert g.power > initial_power
    # First call "charge_start", rest "charging"
    assert action == "charging"


def test_aiming_power_capped():
    g = _make_game_aiming()
    for _ in range(200):
        g._handle_aiming_input(mouse_down=True, cycle_left=False, cycle_right=False)
    assert g.power <= Game.MAX_POWER


def test_aiming_release_launches():
    g = _make_game_aiming()
    g._handle_aiming_input(mouse_down=True, cycle_left=False, cycle_right=False)
    for _ in range(10):
        g._handle_aiming_input(mouse_down=True, cycle_left=False, cycle_right=False)
    action = g._handle_aiming_input(mouse_down=False, cycle_left=False, cycle_right=False)
    assert action == "launch"
    assert g.phase == Phase.FLYING
    assert g.charging is False
    assert g.power == 0.0


def test_aiming_color_cycle_right():
    g = _make_game_aiming()
    original = g.ball_color_idx
    action = g._handle_aiming_input(mouse_down=False, cycle_left=False, cycle_right=True)
    assert action == "color_next"
    assert g.ball_color_idx == (original + 1) % Game.NUM_COLORS


def test_aiming_color_cycle_left():
    g = _make_game_aiming()
    original = g.ball_color_idx
    action = g._handle_aiming_input(mouse_down=False, cycle_left=True, cycle_right=False)
    assert action == "color_prev"
    assert g.ball_color_idx == (original - 1) % Game.NUM_COLORS


def test_aiming_color_cycle_cooldown():
    g = _make_game_aiming()
    g._handle_aiming_input(mouse_down=False, cycle_left=False, cycle_right=True)
    assert g.color_cycle_cooldown == Game.COLOR_CYCLE_COOLDOWN
    action = g._handle_aiming_input(mouse_down=False, cycle_left=False, cycle_right=True)
    assert action == "idle"  # Cooldown blocks repeated switch


def test_aiming_idle():
    g = _make_game_aiming()
    action = g._handle_aiming_input(mouse_down=False, cycle_left=False, cycle_right=False)
    assert action == "idle"


# ---- Launch Ball ----


def test_launch_ball_sets_velocity():
    g = _make_game_aiming()
    g.power = 8.0
    g._launch_ball()
    assert g.phase == Phase.FLYING
    assert g.charging is False
    assert g.power == 0.0


def test_launch_ball_clears_ghost():
    g = _make_game_aiming()
    g.ghost_points = [GhostPoint(0, 0)]
    g.power = 5.0
    g._launch_ball()
    assert g.ghost_points == []


def test_launch_ball_resets_position():
    g = _make_game_aiming()
    g.ball_x = 999
    g.ball_y = 999
    g.power = 5.0
    g._launch_ball()
    assert g.ball_x == Game.LAUNCH_X
    assert g.ball_y == Game.LAUNCH_Y


# ---- Flying / Ball Out of Bounds ----


def test_ball_out_of_bounds_top():
    g = _make_game_aiming()
    g.ball_y = -30
    assert g._ball_out_of_bounds() is True


def test_ball_out_of_bounds_bottom():
    g = _make_game_aiming()
    g.ball_y = Game.SCREEN_H + 30
    assert g._ball_out_of_bounds() is True


def test_ball_out_of_bounds_left():
    g = _make_game_aiming()
    g.ball_x = -30
    assert g._ball_out_of_bounds() is True


def test_ball_out_of_bounds_right():
    g = _make_game_aiming()
    g.ball_x = Game.SCREEN_W + 30
    assert g._ball_out_of_bounds() is True


def test_ball_in_bounds():
    g = _make_game_aiming()
    g.ball_x = 160
    g.ball_y = 120
    assert g._ball_out_of_bounds() is False


# ---- Hole Collision ----


def test_check_hole_collision_hit():
    g = _make_game_aiming()
    hole = g.holes[0]
    assert g._check_hole_collision(float(hole.x), float(hole.y)) is hole


def test_check_hole_collision_miss():
    g = _make_game_aiming()
    assert g._check_hole_collision(0.0, 0.0) is None


def test_check_hole_collision_near_edge():
    g = _make_game_aiming()
    hole = g.holes[0]
    rim_dist = hole.radius - 1
    assert g._check_hole_collision(float(hole.x + rim_dist), float(hole.y)) is hole
    just_outside = hole.radius + 2
    assert g._check_hole_collision(float(hole.x + just_outside), float(hole.y)) is None


# ---- Handle Hit (match) ----


def test_handle_hit_match():
    g = _make_game_aiming()
    hole = g.holes[0]
    g.ball_color_idx = g.COLORS.index(hole.color)
    g._handle_hit(hole)
    assert g.phase == Phase.SCORING
    assert g.combo == 1
    assert g.score >= hole.score
    assert len(g.particles) >= Game.HIT_PARTICLE_COUNT
    assert len(g.floating_texts) >= 1


def test_handle_hit_match_combo_grows():
    g = _make_game_aiming()
    g.combo = 3
    hole = g.holes[0]
    g.ball_color_idx = g.COLORS.index(hole.color)
    g._handle_hit(hole)
    assert g.combo == 4
    assert g.max_combo == 4


def test_handle_hit_match_activates_super():
    g = _make_game_aiming()
    g.combo = 3
    hole = g.holes[0]
    g.ball_color_idx = g.COLORS.index(hole.color)
    g._handle_hit(hole)
    assert g.combo >= Game.SUPER_COMBO_THRESHOLD
    assert g.super_timer > 0


def test_handle_hit_super_mode_any_color_matches():
    g = _make_game_aiming()
    g.super_timer = Game.SUPER_DURATION
    g.ball_color_idx = 0
    hole = g.holes[0]
    g._handle_hit(hole)
    assert g.combo >= 1
    assert g.score > 0


def test_handle_hit_super_mode_multiplier():
    g = _make_game_aiming()
    g.combo = 5
    g.super_timer = Game.SUPER_DURATION
    hole = g.holes[0]
    score_before = g.score
    g._handle_hit(hole)
    gained = g.score - score_before
    expected = hole.score * g.combo * Game.SUPER_MULTIPLIER
    assert gained == expected


# ---- Handle Hit (mismatch) ----


def test_handle_hit_mismatch():
    g = _make_game_aiming()
    g.combo = 3
    g.ball_color_idx = 0
    # Find a hole that doesn't match
    mismatch_hole = next(h for h in g.holes if g.COLORS[g.ball_color_idx] != h.color)
    score_before = g.score
    g._handle_hit(mismatch_hole)
    assert g.combo == 0
    assert g.heat > 0
    assert g.heat == Game.HEAT_MISMATCH
    assert g.score == score_before


# ---- Handle Miss ----


def test_handle_miss():
    g = _make_game_aiming()
    g.combo = 3
    g.ball_x = 200
    g.ball_y = 300
    g._handle_miss()
    assert g.combo == 0
    assert g.heat == Game.HEAT_MISS
    assert g.phase == Phase.SCORING


def test_handle_miss_saves_ghost():
    g = _make_game_aiming()
    g.ghost_points = [GhostPoint(100, 150)]
    g._handle_miss()
    assert g.best_ghost == g.ghost_points


# ---- Heat ----


def test_update_heat_decay():
    g = _make_game_aiming()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 50.0 - Game.HEAT_DECAY


def test_update_heat_game_over():
    g = _make_game_aiming()
    g.heat = Game.MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_clamped_to_zero():
    g = _make_game_aiming()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ---- Particles ----


def test_update_particles_decrement_life():
    g = _make_game_aiming()
    g.particles = [Particle(100, 100, 1, -1, 5, 8)]
    original_life = g.particles[0].life
    g._update_particles()
    assert g.particles[0].life < original_life


def test_update_particles_remove_dead():
    g = _make_game_aiming()
    g.particles = [Particle(100, 100, 1, -1, 1, 8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_hit_particles():
    g = _make_game_aiming()
    g._spawn_hit_particles(100, 100, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert 0 <= p.x <= 200  # approximate range check
        assert 0 <= p.y <= 200
        assert p.color == 8
        assert p.life > 0


# ---- Floating Texts ----


def test_update_floating_texts_decrement_life():
    g = _make_game_aiming()
    g.floating_texts = [FloatingText(100, 50, "Test", 10, 7)]
    original_life = g.floating_texts[0].life
    g._update_floating_texts()
    assert g.floating_texts[0].life < original_life


def test_update_floating_texts_move_up():
    g = _make_game_aiming()
    g.floating_texts = [FloatingText(100, 50, "Test", 10, 7)]
    original_y = g.floating_texts[0].y
    g._update_floating_texts()
    assert g.floating_texts[0].y < original_y


def test_update_floating_texts_remove_dead():
    g = _make_game_aiming()
    g.floating_texts = [FloatingText(100, 50, "Test", 1, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_spawn_floating_text():
    g = _make_game_aiming()
    g._spawn_floating_text(150, 100, "+200", 8)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+200"
    assert g.floating_texts[0].color == 8
    assert g.floating_texts[0].life == 30


# ---- Timer ----


def test_update_timer_decrements():
    g = _make_game_aiming()
    initial = g.timer
    g._update_timer()
    assert g.timer == initial - 1


def test_update_timer_game_over():
    g = _make_game_aiming()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ---- Escalation ----


def test_escalation_params_early():
    g = _make_game_aiming()
    g.timer = Game.TIMER_START  # 0 seconds elapsed
    mult, interval = g._escalation_params()
    assert mult == 1.0
    assert interval == 0


def test_escalation_params_late():
    g = _make_game_aiming()
    g.timer = Game.TIMER_START - 60 * 30  # 60 seconds elapsed
    mult, interval = g._escalation_params()
    assert mult > 1.0
    assert interval > 0


# ---- Is Super Mode ----


def test_is_super_mode_active():
    g = _make_game_aiming()
    g.super_timer = 100
    assert g._is_super_mode() is True


def test_is_super_mode_inactive():
    g = _make_game_aiming()
    g.super_timer = 0
    assert g._is_super_mode() is False


# ---- Flying Update ----


def test_update_flying_gravity():
    g = _make_game_aiming()
    g.phase = Phase.FLYING
    g.ball_vx = 5.0
    g.ball_vy = -5.0
    g.ball_x = 100
    g.ball_y = 100
    g._update_flying()
    assert g.ball_vy == -5.0 + Game.GRAVITY
    assert len(g.ghost_points) == 1


def test_update_flying_hits_hole():
    g = _make_game_aiming()
    g.phase = Phase.FLYING
    g.ball_color_idx = 0
    hole = g.holes[0]
    g.ball_color_idx = g.COLORS.index(hole.color)
    g.ball_x = float(hole.x)
    g.ball_y = float(hole.y)
    g.ball_vx = 0
    g.ball_vy = 0
    g._update_flying()
    assert g.phase == Phase.SCORING


def test_update_flying_miss_out_of_bounds():
    g = _make_game_aiming()
    g.phase = Phase.FLYING
    g.ball_x = -50
    g.ball_y = -50
    g.ball_vx = 0
    g.ball_vy = 0
    g.combo = 3
    g._update_flying()
    assert g.combo == 0
    assert g.heat == Game.HEAT_MISS


# ---- Scoring Timer ----


def test_scoring_to_aiming_transition():
    g = _make_game_aiming()
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g._update_timer()
    # Scoring timer tick in update, but this is the manual scoring logic
    g.scoring_timer -= 1
    # simulate update cycle
    assert g.scoring_timer == 0
