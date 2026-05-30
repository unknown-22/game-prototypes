"""test_imports.py — Headless logic tests for CHAIN KICK (087_chain_kick)."""
from __future__ import annotations

import random
import sys
from pathlib import Path

# Add prototype dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    Ball,
    BALL_COLORS,
    BASE_SCORE,
    COMBO_SCORE_MULT,
    FloatingText,
    GK_Y,
    GOAL_BOTTOM,
    GOAL_CENTER_X,
    GOAL_LEFT,
    GOAL_RIGHT,
    GOAL_TOP,
    Goalkeeper,
    HEAT_GOAL_DEC,
    HEAT_MISS,
    HEAT_SAVE,
    MAX_HEAT,
    Particle,
    PENALTY_X,
    PENALTY_Y,
    Phase,
    RED,
    RESULT_DELAY,
    ROUNDS_TOTAL,
    SHAKE_FRAMES,
    SHOT_SPEED,
    SPEED_BONUS,
    SPEED_BONUS_FRAMES,
    SUPER_BONUS,
    SUPER_COMBO_THRESHOLD,
    Game,
    choose_ball_color,
    compute_ball_trajectory,
    compute_score,
    gk_choose_direction,
    is_in_goal_area,
    resolve_shot,
    update_combo,
    update_heat,
)

# ---------------------------------------------------------------------------
# Factory for headless Game instance
# ---------------------------------------------------------------------------


def _make_game() -> Game:
    """Create a Game instance without pyxel.init (headless-safe)."""
    g = Game.__new__(Game)
    # Pre-init all attributes that _init_state() touches
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.round = 0
    g.rounds_total = ROUNDS_TOTAL
    g.phase = Phase.TITLE
    g.ball_color = RED
    g.prev_ball_colors: list[int] = []
    g.ball = Ball(x=PENALTY_X, y=PENALTY_Y, color=RED)
    g.goalkeeper = Goalkeeper(x=GOAL_CENTER_X, y=GK_Y)
    g.particles: list[Particle] = []
    g.floating_texts: list[FloatingText] = []
    g.aim_x = GOAL_CENTER_X
    g.aim_y = GOAL_CENTER_X
    g.result_timer = 0
    g.last_result = ""
    g.last_shot_label = ""
    g.last_score_delta = 0
    g.shake_frames = 0
    g.is_super = False
    g.title_flash = 0
    g.shot_frame_count = 0
    g._rng = None  # type: ignore
    g._font_path = Path(__file__).with_name("k8x12.bdf")
    # Now init — _init_state() overwrites everything including _rng
    g._init_state()
    # Set seeded RNG AFTER _init_state (which creates an unseeded one)
    g._rng = random.Random(42)
    return g


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestChooseBallColor:
    def test_returns_valid_color(self) -> None:
        rng = random.Random(42)
        for _ in range(50):
            c = choose_ball_color(rng)
            assert c in BALL_COLORS, f"Unexpected color: {c}"


class TestGKChooseDirection:
    def test_returns_valid_tuple(self) -> None:
        rng = random.Random(42)
        direction, tx, ty, gc = gk_choose_direction(0, rng)
        assert direction in (-1, 0, 1)
        assert 60 < tx < 260
        assert 40 < ty < 200
        assert gc in BALL_COLORS

    def test_high_heat_biases_toward_last_shot(self) -> None:
        rng = random.Random(42)
        # High heat with last shot position
        matches = 0
        for _ in range(100):
            direction, tx, ty, gc = gk_choose_direction(
                9, rng, last_shot_x=100, last_shot_y=100,
                prev_ball_colors=[RED, RED, RED],
            )
            if direction == 0:  # left
                matches += 1
        # At heat=9, bias is 0.8, should pick left often
        assert matches > 20, f"Expected high bias, got {matches} left picks"

    def test_guesses_from_previous_colors(self) -> None:
        rng = random.Random(42)
        # Use prev colors to influence guess
        prev_colors = [RED, RED, RED]  # all RED
        red_guesses = 0
        for _ in range(100):
            _, _, _, gc = gk_choose_direction(0, rng, prev_ball_colors=prev_colors)
            if gc == RED:
                red_guesses += 1
        # With 0.7 chance from last 3, should often guess RED
        assert red_guesses > 30, f"Expected frequent RED guesses, got {red_guesses}"


class TestResolveShot:
    def test_super_always_returns_super(self) -> None:
        result = resolve_shot(160, 100, RED, 0, RED, 70, 100, is_super=True)
        assert result == "SUPER"

    def test_miss_left_post(self) -> None:
        result = resolve_shot(GOAL_LEFT, 100, RED, 0, RED, 160, 100, is_super=False)
        assert result == "MISS"

    def test_miss_right_post(self) -> None:
        result = resolve_shot(GOAL_RIGHT, 100, RED, 0, RED, 160, 100, is_super=False)
        assert result == "MISS"

    def test_miss_top_bar(self) -> None:
        result = resolve_shot(100, GOAL_TOP, RED, 0, RED, 160, 100, is_super=False)
        assert result == "MISS"

    def test_miss_bottom(self) -> None:
        result = resolve_shot(100, GOAL_BOTTOM, RED, 0, RED, 160, 100, is_super=False)
        assert result == "MISS"

    def test_goal_when_gk_center(self) -> None:
        result = resolve_shot(150, 100, RED, -1, RED, 160, 100, is_super=False)
        assert result == "GOAL"

    def test_save_when_gk_right_place_right_color(self) -> None:
        # GK dives left, ball shot to left (close to GK dive position), same color
        result = resolve_shot(90, 100, RED, 0, RED, 90, 100, is_super=False)
        assert result == "SAVE"

    def test_goal_when_gk_right_place_wrong_color(self) -> None:
        result = resolve_shot(90, 100, RED, 0, 3, 90, 100, is_super=False)
        assert result == "GOAL"

    def test_goal_when_gk_far_away(self) -> None:
        result = resolve_shot(250, 100, RED, 0, RED, 90, 100, is_super=False)
        assert result == "GOAL"


class TestUpdateCombo:
    def test_save_resets_combo(self) -> None:
        assert update_combo("SAVE", RED, RED, 3) == 0

    def test_miss_resets_combo(self) -> None:
        assert update_combo("MISS", RED, RED, 3) == 0

    def test_same_color_goal_increments(self) -> None:
        assert update_combo("GOAL", RED, RED, 2) == 3

    def test_different_color_goal_resets_to_1(self) -> None:
        assert update_combo("GOAL", 3, RED, 3) == 1

    def test_super_same_color_increments(self) -> None:
        assert update_combo("SUPER", RED, RED, 3) == 4

    def test_combo_from_zero(self) -> None:
        assert update_combo("GOAL", RED, -1, 0) == 1


class TestComputeScore:
    def test_save_returns_zero(self) -> None:
        score, label = compute_score("SAVE", 0, False, 30)
        assert score == 0
        assert label == ""

    def test_miss_returns_zero(self) -> None:
        score, label = compute_score("MISS", 0, False, 30)
        assert score == 0

    def test_basic_goal_no_combo(self) -> None:
        score, label = compute_score("GOAL", 0, False, 200)
        assert score == BASE_SCORE
        assert label == ""

    def test_goal_with_combo(self) -> None:
        score, label = compute_score("GOAL", 3, False, 200)
        assert score == BASE_SCORE + 3 * COMBO_SCORE_MULT

    def test_speed_bonus(self) -> None:
        score, label = compute_score("GOAL", 0, False, 30)
        assert score == BASE_SCORE + SPEED_BONUS
        assert "FAST!" in label

    def test_super_bonus(self) -> None:
        score, label = compute_score("SUPER", 3, True, 200)
        expected = BASE_SCORE + 3 * COMBO_SCORE_MULT + SUPER_BONUS
        assert score == expected
        assert "SUPER!!" in label


class TestUpdateHeat:
    def test_save_increases_heat(self) -> None:
        assert update_heat("SAVE", 5) == 5 + HEAT_SAVE

    def test_miss_increases_heat(self) -> None:
        assert update_heat("MISS", 5) == 5 + HEAT_MISS

    def test_goal_decreases_heat(self) -> None:
        assert update_heat("GOAL", 5) == 5 - HEAT_GOAL_DEC

    def test_heat_caps_at_max(self) -> None:
        assert update_heat("SAVE", MAX_HEAT - 1) <= MAX_HEAT

    def test_heat_floor_at_zero(self) -> None:
        assert update_heat("GOAL", 0) == 0

    def test_super_does_not_change_heat(self) -> None:
        assert update_heat("SUPER", 5) == 5


class TestIsInGoalArea:
    def test_center_is_valid(self) -> None:
        assert is_in_goal_area(160, 100)

    def test_post_area_is_invalid(self) -> None:
        assert not is_in_goal_area(GOAL_LEFT, 100)

    def test_bar_area_is_invalid(self) -> None:
        assert not is_in_goal_area(160, GOAL_TOP)

    def test_outside_is_invalid(self) -> None:
        assert not is_in_goal_area(300, 100)
        assert not is_in_goal_area(160, 250)


class TestComputeBallTrajectory:
    def test_upward_shot(self) -> None:
        vx, vy = compute_ball_trajectory(PENALTY_X, PENALTY_Y, 160, 100, SHOT_SPEED)
        # Should go upward (negative vy)
        assert vy < 0

    def test_left_shot(self) -> None:
        vx, vy = compute_ball_trajectory(PENALTY_X, PENALTY_Y, 100, 100, SHOT_SPEED)
        assert vx < 0

    def test_right_shot(self) -> None:
        vx, vy = compute_ball_trajectory(PENALTY_X, PENALTY_Y, 220, 100, SHOT_SPEED)
        assert vx > 0

    def test_speed_magnitude(self) -> None:
        vx, vy = compute_ball_trajectory(0, 0, 100, 0, 5.0)
        assert abs(vx - 5.0) < 0.01
        assert abs(vy) < 0.01

    def test_zero_distance(self) -> None:
        vx, vy = compute_ball_trajectory(10, 10, 10, 10, 5.0)
        assert vx == 0.0
        assert vy == -5.0


# ---------------------------------------------------------------------------
# Game class structural tests
# ---------------------------------------------------------------------------


class TestGameInit:
    def test_game_has_required_phases(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.SHOT_ANIM in Phase
        assert Phase.RESULT in Phase
        assert Phase.GAME_OVER in Phase

    def test_game_has_pure_functions(self) -> None:
        for fn in [choose_ball_color, gk_choose_direction, resolve_shot,
                    update_combo, compute_score, update_heat,
                    is_in_goal_area, compute_ball_trajectory]:
            assert callable(fn), f"Function {fn} is not callable"


class TestGameState:
    def test_make_game_initial_state(self) -> None:
        g = _make_game()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0
        assert g.round == 0
        assert g.rounds_total == ROUNDS_TOTAL
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_reset_clears_state(self) -> None:
        g = _make_game()
        # Mess with state
        g.score = 999
        g.combo = 5
        g.heat = 8
        g.particles = [Particle(0, 0, 0, 0, 10, RED)]
        g.floating_texts = [FloatingText(0, 0, "test", RED, 10)]
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0


class TestGameShoot:
    def test_shoot_activates_ball(self) -> None:
        g = _make_game()
        g._start_game()
        g.aim_x = 160
        g.aim_y = 100
        g._shoot()
        assert g.ball.active
        assert g.phase == Phase.SHOT_ANIM

    def test_super_kick_when_combo_high(self) -> None:
        g = _make_game()
        g._start_game()
        g.combo = SUPER_COMBO_THRESHOLD
        g.prev_ball_colors = [RED, RED, RED]
        g.aim_x = 160
        g.aim_y = 100
        g._shoot()
        assert g.is_super
        assert g.ball.color == 7  # WHITE

    def test_no_super_when_combo_low(self) -> None:
        g = _make_game()
        g._start_game()
        g.combo = 2
        g.prev_ball_colors = [RED, RED]
        g.aim_x = 160
        g.aim_y = 100
        g._shoot()
        assert not g.is_super


class TestGameResultResolution:
    def test_resolve_goal_increments_round(self) -> None:
        g = _make_game()
        g._start_game()
        # Simulate shooting to center where GK won't save (GK is at center but direction=-1)
        g.combo = 0
        g.prev_ball_colors = []
        g.aim_x = 160
        g.aim_y = 100
        g.ball_color = RED
        g._shoot()
        # Manually move ball to target
        g.ball.x = g.ball.target_x
        g.ball.y = g.ball.target_y
        # Set GK to not dive (direction=-1 means stay center)
        g.goalkeeper.direction = -1
        g._resolve_result()
        assert g.last_result == "GOAL"
        assert g.phase == Phase.RESULT
        assert g.result_timer == RESULT_DELAY

    def test_result_transitions_to_playing(self) -> None:
        g = _make_game()
        g._start_game()
        initial_round = g.round
        g.phase = Phase.RESULT
        g.result_timer = 1
        g.heat = 0
        g._update_result()  # decrements timer to 0, transitions
        assert g.round == initial_round + 1
        assert g.phase == Phase.PLAYING

    def test_result_game_over_when_max_heat(self) -> None:
        g = _make_game()
        g._start_game()
        g.phase = Phase.RESULT
        g.heat = MAX_HEAT
        g.result_timer = 1
        g._update_result()
        assert g.phase == Phase.GAME_OVER

    def test_result_game_over_at_max_rounds(self) -> None:
        g = _make_game()
        g._start_game()
        g.round = ROUNDS_TOTAL
        g.phase = Phase.RESULT
        g.heat = 0
        g.result_timer = 1
        g._update_result()
        assert g.phase == Phase.GAME_OVER


class TestGameStart:
    def test_start_game_sets_playing(self) -> None:
        g = _make_game()
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.round == 1
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0

    def test_setup_round_creates_ball(self) -> None:
        g = _make_game()
        g._start_game()
        g._setup_round()
        assert g.ball_color in BALL_COLORS
        assert g.ball.x == PENALTY_X
        assert g.ball.y == PENALTY_Y


class TestParticlesAndFloatingText:
    def test_particle_lifecycle(self) -> None:
        g = _make_game()
        g._spawn_particles(100, 100, RED, 3)
        assert len(g.particles) == 3
        g._update_particles()
        # Particles should still be alive (life 8-20)
        assert len(g.particles) == 3
        # Kill all
        for p in g.particles:
            p.life = 1
        g._update_particles()
        assert len(g.particles) == 0

    def test_floating_text_lifecycle(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100, 100, "TEST", RED, 2)
        assert len(g.floating_texts) == 1
        g._update_floating_texts()
        # life=2, decremented to 1, still alive
        assert len(g.floating_texts) == 1
        g._update_floating_texts()
        # life=1, decremented to 0, removed
        assert len(g.floating_texts) == 0

    def test_goal_spawns_particles(self) -> None:
        g = _make_game()
        g._start_game()
        g.aim_x = 160
        g.aim_y = 100
        g.ball_color = RED
        g.prev_ball_colors = [RED]
        g.combo = 1
        g._shoot()
        g.ball.x = g.ball.target_x
        g.ball.y = g.ball.target_y
        g.goalkeeper.direction = -1  # center = auto goal
        initial_particles = len(g.particles)
        g._resolve_result()
        assert len(g.particles) > initial_particles
        assert g.last_result == "GOAL"


class TestConstants:
    def test_color_list_has_four_colors(self) -> None:
        assert len(BALL_COLORS) == 4

    def test_constants_reasonable(self) -> None:
        assert ROUNDS_TOTAL == 10
        assert MAX_HEAT == 10
        assert SUPER_COMBO_THRESHOLD == 3
        assert SUPER_BONUS == 50
        assert BASE_SCORE == 10
        assert COMBO_SCORE_MULT == 5
        assert HEAT_SAVE == 2
        assert HEAT_MISS == 1
        assert HEAT_GOAL_DEC == 1
        assert SHAKE_FRAMES == 8


class TestDataClasses:
    def test_ball_defaults(self) -> None:
        b = Ball(160, 200)
        assert b.x == 160
        assert b.y == 200
        assert not b.active
        assert b.vx == 0.0

    def test_goalkeeper_defaults(self) -> None:
        gk = Goalkeeper()
        assert gk.x == 160.0
        assert not gk.diving
        assert gk.direction == -1

    def test_particle(self) -> None:
        p = Particle(100, 100, 1.0, -2.0, 10, RED)
        assert p.life == 10
        assert p.color == RED
        assert p.size == 2


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results: dict[str, bool] = {}
    for name, obj in dict(globals()).items():
        if name.startswith("Test") and callable(obj):
            test_cls = obj
            for attr_name in dir(test_cls):
                if attr_name.startswith("test_"):
                    test_name = f"{name}.{attr_name}"
                    try:
                        getattr(test_cls(), attr_name)()
                        results[test_name] = True
                        print(f"  PASS {test_name}")
                    except Exception as e:
                        results[test_name] = False
                        print(f"  FAIL {test_name}: {e}")

    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"\nResults: {passed} passed, {failed} failed, {len(results)} total")
    if failed > 0:
        sys.exit(1)
