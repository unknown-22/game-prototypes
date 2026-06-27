import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    BASE_SCORE_PER_HIT,
    HEAT_MAX,
    HEAT_PER_MISS,
    MARBLE_RADIUS,
    MAX_FALL_SPEED,
    MAX_ROUNDS,
    PEG_RADIUS,
    ROUND_END_DELAY,
    SUPER_DURATION,
    FloatingText,
    Game,
    Marble,
    Particle,
    Peg,
    Phase,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.round_num = 0
    g.max_rounds = MAX_ROUNDS
    g.super_timer = 0
    g.drop_x = 160.0
    g.marble = None
    g.pegs = []
    g.particles = []
    g.floating_texts = []
    g.best_score = 0
    g.ghost_path = []
    g.shake_frames = 0
    g.round_end_timer = 0
    g.best_round_score = 0
    g.round_score_start = 0
    g._current_path = []
    g._path_sample_counter = 0
    g._spawn_pegs()
    return g


# --- Peg spawning ---
class TestPegSpawning:
    def test_spawns_pegs(self) -> None:
        g = make_game()
        assert len(g.pegs) > 0
        for peg in g.pegs:
            assert peg.color in [8, 3, 6, 10]
            assert peg.hit is False

    def test_pegs_in_field_bounds(self) -> None:
        g = make_game()
        for peg in g.pegs:
            assert 30 <= peg.x <= 290
            assert 50 <= peg.y <= 230

    def test_respawn_changes_colors(self) -> None:
        g = make_game()
        _colors1 = [p.color for p in g.pegs]
        g._spawn_pegs()
        _colors2 = [p.color for p in g.pegs]


# --- Marble dropping ---
class TestMarbleDrop:
    def test_drop_marble_creates_marble(self) -> None:
        g = make_game()
        g._drop_marble(160.0)
        assert g.marble is not None
        m = g.marble
        assert m.x == 160.0
        assert m.active is True
        assert m.color in [8, 3, 6, 10]

    def test_drop_resets_combo(self) -> None:
        g = make_game()
        g.combo = 5
        g.score = 100
        g._drop_marble(160.0)
        assert g.combo == 0
        assert g.round_score_start == 100


# --- Collision detection ---
class TestPegCollision:
    def test_collision_detected(self) -> None:
        g = make_game()
        peg = Peg(x=160.0, y=100.0, color=8)
        marble = Marble(x=160.0, y=100.0, vx=0, vy=0, color=8)
        assert g._check_peg_collision(marble, peg) is True

    def test_no_collision_far(self) -> None:
        g = make_game()
        peg = Peg(x=0.0, y=0.0, color=8)
        marble = Marble(x=200.0, y=200.0, vx=0, vy=0, color=8)
        assert g._check_peg_collision(marble, peg) is False

    def test_collision_edge_distance(self) -> None:
        g = make_game()
        peg = Peg(x=160.0, y=100.0, color=8)
        r_sum = MARBLE_RADIUS + PEG_RADIUS
        marble = Marble(x=160.0 + r_sum - 0.1, y=100.0, vx=0, vy=0, color=8)
        assert g._check_peg_collision(marble, peg) is True
        marble2 = Marble(x=160.0 + r_sum + 0.1, y=100.0, vx=0, vy=0, color=8)
        assert g._check_peg_collision(marble2, peg) is False


# --- Collision physics ---
class TestCollisionPhysics:
    def test_bounce_reverses_velocity(self) -> None:
        g = make_game()
        peg = Peg(x=160.0, y=100.0, color=8)
        marble = Marble(x=160.0, y=99.0, vx=0, vy=3.0, color=8)
        g._resolve_collision_physics(marble, peg)
        # Should bounce upward
        assert marble.vy < 0

    def test_marble_pushed_out_of_overlap(self) -> None:
        g = make_game()
        peg = Peg(x=160.0, y=100.0, color=8)
        marble = Marble(x=160.0, y=100.0, vx=0, vy=0, color=8)
        g._resolve_collision_physics(marble, peg)
        dist = ((marble.x - peg.x) ** 2 + (marble.y - peg.y) ** 2) ** 0.5
        assert dist >= (MARBLE_RADIUS + PEG_RADIUS) - 0.01


# --- Combo and scoring ---
class TestComboScoring:
    def test_combo_multiplier_zero(self) -> None:
        g = make_game()
        assert g._get_combo_multiplier() == 1.0

    def test_combo_multiplier_increases(self) -> None:
        g = make_game()
        g.combo = 2
        assert g._get_combo_multiplier() == 2.0

    def test_base_score(self) -> None:
        g = make_game()
        assert g._get_score_for_hit() == BASE_SCORE_PER_HIT

    def test_score_with_combo(self) -> None:
        g = make_game()
        g.combo = 3
        expected = int(BASE_SCORE_PER_HIT * (1.0 + 3 * 0.5))
        assert g._get_score_for_hit() == expected

    def test_score_with_super(self) -> None:
        g = make_game()
        g.super_timer = 100
        assert g._get_score_for_hit() == BASE_SCORE_PER_HIT * 3

    def test_score_minimum_one(self) -> None:
        g = make_game()
        g.combo = -100
        assert g._get_score_for_hit() >= 1

    def test_max_combo_tracks_highest(self) -> None:
        g = make_game()
        g._drop_marble(160.0)
        g.marble = Marble(x=160, y=50, vx=0, vy=1, color=8)
        peg = Peg(x=160, y=60, color=8, hit=False)
        g.pegs = [peg]
        # hit same color → combo 1
        g._resolve_peg_hit(peg, g.marble, False)
        assert g.combo == 1
        assert g.max_combo == 1


# --- Peg hit resolution ---
class TestPegHitResolution:
    def test_match_increments_combo(self) -> None:
        g = make_game()
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=8)
        g._resolve_peg_hit(peg, marble, False)
        assert g.combo == 1

    def test_mismatch_resets_combo(self) -> None:
        g = make_game()
        g.combo = 3
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=3)
        g._resolve_peg_hit(peg, marble, False)
        assert g.combo == 0

    def test_mismatch_adds_heat(self) -> None:
        g = make_game()
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=3)
        g._resolve_peg_hit(peg, marble, False)
        assert g.heat == HEAT_PER_MISS

    def test_heat_capped(self) -> None:
        g = make_game()
        g.heat = HEAT_MAX
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=3)
        g._resolve_peg_hit(peg, marble, False)
        assert g.heat <= HEAT_MAX

    def test_match_adds_score(self) -> None:
        g = make_game()
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=8)
        g._resolve_peg_hit(peg, marble, False)
        assert g.score > 0

    def test_match_spawns_floating_text(self) -> None:
        g = make_game()
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=8)
        g._resolve_peg_hit(peg, marble, False)
        assert len(g.floating_texts) == 1

    def test_mismatch_spawns_miss_text(self) -> None:
        g = make_game()
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=3)
        g._resolve_peg_hit(peg, marble, False)
        assert len(g.floating_texts) == 1
        assert "MISS" in g.floating_texts[0].text


# --- SUPER mode ---
class TestSuperMode:
    def test_super_activates_at_combo_4(self) -> None:
        g = make_game()
        g.combo = 3
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=8)
        g._resolve_peg_hit(peg, marble, False)
        assert g.super_timer == SUPER_DURATION
        assert g.shake_frames == 15

    def test_super_during_super_no_combo_reset_on_mismatch(self) -> None:
        g = make_game()
        g.super_timer = 100
        g.combo = 2
        peg = Peg(x=160, y=60, color=8)
        marble = Marble(x=160, y=50, vx=0, vy=1, color=3)  # different color
        g._resolve_peg_hit(peg, marble, True)
        assert g.combo == 3  # incremented, not reset
        assert g.heat == 0.0  # no heat added

    def test_super_timer_decrements_in_update(self) -> None:
        g = make_game()
        g.super_timer = 10
        g.marble = Marble(x=160, y=50, vx=0, vy=1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.super_timer == 9


# --- Round advancement ---
class TestRoundAdvance:
    def test_advance_round_increments(self) -> None:
        g = make_game()
        g.round_num = 1
        g.marble = Marble(x=160, y=250, vx=0, vy=1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.phase == Phase.ROUND_END
        assert g.round_num == 2

    def test_advance_round_10_to_game_over(self) -> None:
        g = make_game()
        g.round_num = 10
        g.marble = Marble(x=160, y=250, vx=0, vy=1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.phase == Phase.GAME_OVER

    def test_heat_max_triggers_game_over_on_advance(self) -> None:
        g = make_game()
        g.heat = HEAT_MAX
        g.marble = None
        g._advance_round()
        assert g.phase == Phase.GAME_OVER


# --- Round end timer ---
class TestRoundEnd:
    def test_round_end_timer_set(self) -> None:
        g = make_game()
        g.round_num = 1
        g.marble = Marble(x=160, y=250, vx=0, vy=1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.round_end_timer == ROUND_END_DELAY

    def test_round_end_transitions_to_aiming(self) -> None:
        g = make_game()
        g.phase = Phase.ROUND_END
        g.round_end_timer = 1
        g._update_round_end()
        assert g.phase == Phase.AIMING


# --- Game state ---
class TestGameState:
    def test_start_game_resets_and_sets_aiming(self) -> None:
        g = make_game()
        g.phase = Phase.TITLE
        g.score = 50
        g.start_game()
        assert g.phase == Phase.AIMING
        assert g.score == 0
        assert g.round_num == 1

    def test_end_game_updates_best_score(self) -> None:
        g = make_game()
        g.score = 500
        g._end_game()
        assert g.best_score == 500
        assert g.phase == Phase.GAME_OVER

    def test_reset_clears_all_state(self) -> None:
        g = make_game()
        g.score = 500
        g.combo = 3
        g.heat = 50.0
        g.round_num = 5
        g.super_timer = 30
        g.particles = [Particle(x=0, y=0, vx=1, vy=1, life=10, max_life=10, color=8)]
        g.floating_texts = [FloatingText(x=0, y=0, text="test", life=10, max_life=10, color=7)]
        g.ghost_path = [(1.0, 2.0)]
        g.shake_frames = 10

        g.reset()

        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.round_num == 0
        assert g.super_timer == 0
        assert g.marble is None
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert g.shake_frames == 0
        assert len(g.ghost_path) == 0
        assert g.best_round_score == 0


# --- Physics ---
class TestPhysics:
    def test_gravity_increases_vy(self) -> None:
        g = make_game()
        g.marble = Marble(x=160, y=50, vx=0, vy=0, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.marble.vy > 0

    def test_vy_clamped_at_max(self) -> None:
        g = make_game()
        g.marble = Marble(x=160, y=50, vx=0, vy=MAX_FALL_SPEED + 1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.marble.vy == MAX_FALL_SPEED

    def test_wall_bounce_left(self) -> None:
        g = make_game()
        g.marble = Marble(x=1, y=50, vx=-2, vy=1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.marble.vx > 0  # bounced right

    def test_wall_bounce_right(self) -> None:
        g = make_game()
        g.marble = Marble(x=319, y=50, vx=2, vy=1, color=8)
        g.phase = Phase.FALLING
        g._update_falling()
        assert g.marble.vx < 0  # bounced left


# --- Particle system ---
class TestParticles:
    def test_spawn_hit_particles(self) -> None:
        g = make_game()
        g._spawn_hit_particles(160, 100, 8, False)
        assert len(g.particles) > 0
        for p in g.particles:
            assert p.life > 0
            assert p.max_life > 0

    def test_spawn_super_particles_more(self) -> None:
        g = make_game()
        g._spawn_hit_particles(160, 100, 8, False)
        normal_count = len(g.particles)
        g.particles.clear()
        g._spawn_hit_particles(160, 100, 8, True)
        super_count = len(g.particles)
        assert super_count > normal_count

    def test_particles_decay_and_remove(self) -> None:
        g = make_game()
        g.particles = [
            Particle(x=0, y=0, vx=0, vy=0, life=0, max_life=10, color=8),
            Particle(x=0, y=0, vx=0, vy=0, life=-1, max_life=10, color=8),
            Particle(x=0, y=0, vx=0, vy=0, life=5, max_life=10, color=8),
        ]
        g._update_particles()
        assert len(g.particles) == 1


# --- Floating text system ---
class TestFloatingTexts:
    def test_floating_texts_decay_and_remove(self) -> None:
        g = make_game()
        g.floating_texts = [
            FloatingText(x=0, y=0, text="test", life=0, max_life=20, color=7),
            FloatingText(x=0, y=0, text="test2", life=5, max_life=20, color=7),
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
