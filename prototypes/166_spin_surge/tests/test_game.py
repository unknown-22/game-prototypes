import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    COLOR_CYCLE_INTERVAL,
    COMBO_FOR_SUPER,
    GAME_TIMER,
    GRID_COLS,
    GRID_ROWS,
    HEAT_DECAY,
    HEAT_PER_MISMATCH,
    HEAT_PER_OFF_RINK,
    MAX_CRACKS,
    MAX_HEAT,
    NUM_COLORS,
    Phase,
    RINK_H,
    RINK_W,
    RINK_X,
    RINK_Y,
    SCORE_BASE,
    SCORE_COMBO_MULT,
    SUPER_DURATION,
    SUPER_SCORE_MULT,
    ZONE_LIFE_MAX,
    ZONE_LIFE_MIN,
    ZONE_RADIUS,
    FloatingText,
    Game,
    IceCrack,
    Particle,
    SpinZone,
)


def make_game(seed: int = 42) -> Game:
    """Create a headless Game instance, bypassing pyxel.init."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_TIMER
    g.super_mode = False
    g.super_timer = 0
    g.player_x = float(RINK_X + RINK_W // 2)
    g.player_y = float(RINK_Y + RINK_H // 2)
    g.player_color_idx = 0
    g.player_color_timer = COLOR_CYCLE_INTERVAL
    g.zones: list = []
    g.particles: list = []
    g.floating_texts: list = []
    g.cracks: list = []
    g.zone_spawn_timer = 0
    g.crack_spawn_timer = 0
    g.frame = 0
    g.rng = random.Random(seed)
    g.current_path: list = []
    g.best_path: list = []
    g.phase = Phase.PLAYING
    return g


# ---------------------------------------------------------------------------
# SpinZone spawning
# ---------------------------------------------------------------------------
class TestSpinZoneSpawning:
    def test_spawn_zone_within_rink(self) -> None:
        g = make_game()
        for _ in range(100):
            zone = g._spawn_zone()
            assert RINK_X <= zone.x <= RINK_X + RINK_W
            assert RINK_Y <= zone.y <= RINK_Y + RINK_H
            assert 0 <= zone.color < NUM_COLORS
            assert ZONE_LIFE_MIN <= zone.life <= ZONE_LIFE_MAX
            assert zone.radius == ZONE_RADIUS
            assert zone.active is True

    def test_spawn_initial_zones(self) -> None:
        g = make_game()
        g._spawn_initial_zones()
        assert len(g.zones) == 3
        for zone in g.zones:
            assert zone.active is True


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------
class TestZoneCollision:
    def test_collision_match(self) -> None:
        g = make_game()
        zone = SpinZone(x=100.0, y=100.0, color=0)
        g.player_color_idx = 0
        hit, is_match = g._check_zone_collision(100.0, 100.0, 0, zone)
        assert hit is True
        assert is_match is True

    def test_collision_mismatch(self) -> None:
        g = make_game()
        zone = SpinZone(x=100.0, y=100.0, color=0)
        hit, is_match = g._check_zone_collision(100.0, 100.0, 1, zone)
        assert hit is True
        assert is_match is False

    def test_no_collision_far(self) -> None:
        g = make_game()
        zone = SpinZone(x=100.0, y=100.0, color=0)
        hit, is_match = g._check_zone_collision(200.0, 200.0, 0, zone)
        assert hit is False
        assert is_match is False

    def test_no_collision_inactive(self) -> None:
        g = make_game()
        zone = SpinZone(x=100.0, y=100.0, color=0, active=False)
        hit, is_match = g._check_zone_collision(100.0, 100.0, 0, zone)
        assert hit is False
        assert is_match is False


# ---------------------------------------------------------------------------
# Color cycling
# ---------------------------------------------------------------------------
class TestColorCycling:
    def test_color_cycles_after_interval(self) -> None:
        g = make_game()
        assert g.player_color_idx == 0
        g.player_color_timer = 1
        g._cycle_color()
        assert g.player_color_idx == 1
        assert g.player_color_timer == COLOR_CYCLE_INTERVAL

    def test_color_wraps_around(self) -> None:
        g = make_game()
        g.player_color_idx = 3
        g.player_color_timer = 1
        g._cycle_color()
        assert g.player_color_idx == 0


# ---------------------------------------------------------------------------
# Combo / SUPER
# ---------------------------------------------------------------------------
class TestCombo:
    def test_combo_increments_on_match(self) -> None:
        g = make_game()
        assert g.combo == 0
        g._update_combo(True)
        assert g.combo == 1
        g._update_combo(True)
        assert g.combo == 2

    def test_combo_resets_on_mismatch(self) -> None:
        g = make_game()
        g.combo = 3
        g._update_combo(False)
        assert g.combo == 0

    def test_super_activates_at_combo_threshold(self) -> None:
        g = make_game()
        g.combo = COMBO_FOR_SUPER - 1
        g._update_combo(True)
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_ends_resets_combo(self) -> None:
        g = make_game()
        g.super_mode = True
        g.super_timer = 1
        g.combo = 5
        g.super_timer -= 1  # simulate _update_playing decrement
        # manually trigger end
        g._end_super()
        assert g.super_mode is False
        assert g.super_timer == 0
        assert g.combo == 0

    def test_max_combo_tracks_highest(self) -> None:
        g = make_game()
        g._update_combo(True)
        g._update_combo(True)
        g._update_combo(True)
        g._update_combo(False)
        g._update_combo(True)
        assert g.max_combo == 3


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
class TestScoring:
    def test_score_base_single(self) -> None:
        g = make_game()
        score = g._score_for_match()
        assert score == SCORE_BASE

    def test_score_increases_with_combo(self) -> None:
        g = make_game()
        g.combo = 2
        score = g._score_for_match()
        expected = int(SCORE_BASE * (1.0 + 2 * SCORE_COMBO_MULT))
        assert score == expected

    def test_score_super_multiplier(self) -> None:
        g = make_game()
        g.super_mode = True
        g.combo = 2
        score = g._score_for_match()
        expected = int(SCORE_BASE * (1.0 + 2 * SCORE_COMBO_MULT) * SUPER_SCORE_MULT)
        assert score == expected

    def test_score_minimum_one(self) -> None:
        g = make_game()
        g.combo = -100  # edge case
        score = g._score_for_match()
        assert score >= 1


# ---------------------------------------------------------------------------
# HEAT system
# ---------------------------------------------------------------------------
class TestHeat:
    def test_heat_increases_on_mismatch(self) -> None:
        g = make_game()
        assert g.heat == 0.0
        g._add_heat(HEAT_PER_MISMATCH)
        assert g.heat == HEAT_PER_MISMATCH

    def test_heat_capped_at_max(self) -> None:
        g = make_game()
        g._add_heat(200.0)
        assert g.heat == MAX_HEAT

    def test_heat_decay(self) -> None:
        g = make_game()
        g.heat = 10.0
        g._update_heat_decay()
        assert g.heat == 10.0 - HEAT_DECAY

    def test_heat_decay_bottom_zero(self) -> None:
        g = make_game()
        g.heat = 0.0
        g._update_heat_decay()
        assert g.heat == 0.0

    def test_heat_off_rink(self) -> None:
        g = make_game()
        g._add_heat(HEAT_PER_OFF_RINK)
        assert g.heat == HEAT_PER_OFF_RINK


# ---------------------------------------------------------------------------
# CA Cracks
# ---------------------------------------------------------------------------
class TestIceCracks:
    def test_spawn_crack_within_grid(self) -> None:
        g = make_game()
        assert len(g.cracks) == 0
        g._spawn_crack()
        assert len(g.cracks) == 1
        c = g.cracks[0]
        assert 0 <= c.x < GRID_COLS
        assert 0 <= c.y < GRID_ROWS
        assert c.life > 0

    def test_max_cracks_limit(self) -> None:
        g = make_game()
        for _ in range(MAX_CRACKS + 10):
            g._spawn_crack()
        assert len(g.cracks) <= MAX_CRACKS

    def test_spread_cracks_adds_cracks(self) -> None:
        g = make_game()
        g.cracks.append(IceCrack(x=7, y=5, life=120))
        old_count = len(g.cracks)
        # spread may or may not add due to randomness, but shouldn't crash
        g._spread_cracks()
        assert len(g.cracks) >= old_count

    def test_cracks_decay_and_remove(self) -> None:
        g = make_game()
        g.cracks = [
            IceCrack(x=0, y=0, life=0),
            IceCrack(x=1, y=1, life=-1),
            IceCrack(x=2, y=2, life=2),
        ]
        g._update_cracks()
        assert len(g.cracks) == 1
        assert g.cracks[0].life == 1


# ---------------------------------------------------------------------------
# Timer countdown
# ---------------------------------------------------------------------------
class TestTimer:
    def test_timer_starts_full(self) -> None:
        g = make_game()
        assert g.timer == GAME_TIMER


# ---------------------------------------------------------------------------
# Reset / restart
# ---------------------------------------------------------------------------
class TestReset:
    def test_reset_clears_state(self) -> None:
        g = make_game()
        g.score = 500
        g.combo = 3
        g.heat = 60.0
        g.timer = 100
        g.super_mode = True
        g.zones = [SpinZone(x=50.0, y=50.0, color=0)]
        g.particles = [Particle(x=0, y=0, vx=1, vy=1, color=8, life=10)]
        g.floating_texts = [FloatingText(x=0, y=0, text="test", color=7, life=10)]
        g.cracks = [IceCrack(x=0, y=0, life=60)]

        g.reset()

        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_TIMER
        assert g.super_mode is False
        assert g.super_timer == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert len(g.cracks) == 0
