"""test_imports.py — Headless logic tests for TIGHTROPE SURGE."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    BALANCE_DRIFT,
    BALANCE_RANGE,
    HEAT_DECAY,
    HEAT_PER_MISS,
    MAX_HEAT,
    NUM_GEM_COLORS,
    SPEED_INITIAL,
    SPEED_MAX,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    Gem,
    Game,
    Particle,
    Phase,
    Star,
    WindGust,
)


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() will touch
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.balance = 0.0
    g.distance = 0.0
    g.speed = SPEED_INITIAL
    g.super_timer = 0
    g.gems = []
    g.particles = []
    g.winds = []
    g.player_color_index = 0
    g.player_y_offset = 0.0
    g.shake_frames = 0
    g.shake_intensity = 0
    g.wind_timer = 0
    g.last_gem_x = 0.0
    g.frame = 0
    g.game_over_flash = 0
    g.stars = []
    g.title_particles = []
    g._rng = random.Random(42)
    g.reset()
    # Override RNG after reset (reset() creates a new unseeded Random())
    g._rng = random.Random(42)
    return g


class TestDataclasses:
    """Verify dataclass field types and construction."""

    def test_gem_creation(self) -> None:
        gem = Gem(x=100.0, y=160, color_index=2)
        assert gem.x == 100.0
        assert gem.y == 160
        assert gem.color_index == 2
        assert gem.collected is False

    def test_gem_collected(self) -> None:
        gem = Gem(x=50.0, y=158, color_index=1, collected=True)
        assert gem.collected is True

    def test_particle_creation(self) -> None:
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.5
        assert p.vy == -2.0
        assert p.life == 15
        assert p.color == 8
        assert p.gravity == 0.0
        assert p.size == 2

    def test_particle_with_gravity(self) -> None:
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=7, gravity=0.15)
        assert p.gravity == 0.15

    def test_wind_gust_creation(self) -> None:
        w = WindGust(direction=-1, strength=0.02, duration=40, color=8)
        assert w.direction == -1
        assert w.strength == 0.02
        assert w.duration == 40
        assert w.color == 8

    def test_star_creation(self) -> None:
        s = Star(x=100, y=50, brightness=2)
        assert s.x == 100
        assert s.y == 50
        assert s.brightness == 2


class TestGameInit:
    """Verify game state after reset."""

    def test_initial_phase(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE

    def test_initial_score(self) -> None:
        g = _make_game()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0

    def test_initial_balance(self) -> None:
        g = _make_game()
        assert g.balance == 0.0
        assert -1.0 <= g.balance <= 1.0

    def test_initial_heat(self) -> None:
        g = _make_game()
        assert g.heat == 0.0

    def test_initial_speed(self) -> None:
        g = _make_game()
        assert g.speed == SPEED_INITIAL

    def test_initial_super_timer(self) -> None:
        g = _make_game()
        assert g.super_timer == 0

    def test_initial_empty_collections(self) -> None:
        g = _make_game()
        assert g.gems == []
        assert g.particles == []
        assert g.winds == []

    def test_player_screen_x_centered(self) -> None:
        g = _make_game()
        # balance=0 → centered
        from main import SCREEN_W
        assert g._player_screen_x() == SCREEN_W // 2

    def test_player_screen_x_left(self) -> None:
        g = _make_game()
        from main import SCREEN_W
        g.balance = 1.0  # positive balance → SCREEN_W//2 - 1*60 = 100 (left on screen)
        assert abs(g._player_screen_x() - (SCREEN_W // 2 - BALANCE_RANGE)) < 0.01

    def test_player_screen_x_right(self) -> None:
        g = _make_game()
        from main import SCREEN_W
        g.balance = -1.0  # negative balance → SCREEN_W//2 - (-1*60) = 220 (right on screen)
        assert abs(g._player_screen_x() - (SCREEN_W // 2 + BALANCE_RANGE)) < 0.01


class TestGemCollection:
    """Verify gem collection logic: combo, score, heat."""

    def test_same_color_combo_up(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        gem = Gem(x=100.0, y=160, color_index=0)
        g._collect_gem(gem)
        assert gem.collected is True
        assert g.combo == 1
        assert g.score > 0

    def test_same_color_combo_chain(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        for i in range(3):
            gem = Gem(x=float(100 + i * 10), y=160, color_index=0)
            g._collect_gem(gem)
        assert g.combo == 3
        assert g.max_combo == 3

    def test_wrong_color_resets_combo(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        g.combo = 3
        g.max_combo = 3
        # Collect wrong color
        gem = Gem(x=100.0, y=160, color_index=1)
        g._collect_gem(gem)
        assert g.combo == 0
        # max_combo should still be 3
        assert g.max_combo == 3

    def test_wrong_color_adds_heat(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        g.heat = 20.0
        gem = Gem(x=100.0, y=160, color_index=1)
        g._collect_gem(gem)
        assert g.heat == 20.0 + HEAT_PER_MISS

    def test_heat_clamped_at_max(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        g.heat = MAX_HEAT - 5
        gem = Gem(x=100.0, y=160, color_index=1)
        g._collect_gem(gem)
        assert g.heat == MAX_HEAT

    def test_collect_updates_player_color(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        gem = Gem(x=100.0, y=160, color_index=3)
        g._collect_gem(gem)
        assert g.player_color_index == 3

    def test_max_combo_tracking(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        # Build combo to 3
        for i in range(3):
            g._collect_gem(Gem(x=float(i * 10), y=160, color_index=0))
        assert g.max_combo == 3
        # Wrong color resets combo but max stays
        g._collect_gem(Gem(x=100.0, y=160, color_index=1))
        assert g.combo == 0
        assert g.max_combo == 3
        # Build to 5
        for i in range(5):
            g._collect_gem(Gem(x=float(200 + i * 10), y=160, color_index=1))
        assert g.max_combo == 5

    def test_score_multiplier_during_super(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.player_color_index = 0
        score_before = g.score
        g._collect_gem(Gem(x=100.0, y=160, color_index=0))
        # SUPER gives 3x multiplier
        assert g.score - score_before >= 30  # (10 + 1*5) * 3 = 45


class TestSuperMode:
    """Verify SUPER BALANCE activation, duration, and immunity."""

    def test_activate_super_at_threshold(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        g.combo = SUPER_COMBO_THRESHOLD - 1  # combo = 3
        gem = Gem(x=100.0, y=160, color_index=0)
        g._collect_gem(gem)
        assert g.combo == SUPER_COMBO_THRESHOLD
        assert g.super_timer == SUPER_DURATION

    def test_super_not_reactivate_during_super(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.combo = 5
        g.player_color_index = 0
        gem = Gem(x=100.0, y=160, color_index=0)
        g._collect_gem(gem)
        # Should still be 100 (not reset to SUPER_DURATION)
        assert g.super_timer == 100

    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_timer = 10
        g._update_world(False, False)
        assert g.super_timer == 9

    def test_super_deactivates_at_zero(self) -> None:
        g = _make_game()
        g.super_timer = 1
        g._update_world(False, False)
        assert g.super_timer == 0

    def test_wind_immunity_during_super(self) -> None:
        g = _make_game()
        g.super_timer = 50
        g.balance = 0.5
        g.winds.append(WindGust(direction=1, strength=0.05, duration=10, color=12))
        g._update_world(False, False)
        # Balance drift is still active during SUPER (drifts toward center)
        # Wind immunity means wind didn't ADD extra push beyond drift
        # With only drift: 0.5 → 0.5 - 0.005 = 0.495
        # With wind immunity: same as drift-only result
        assert abs(g.balance - 0.495) < 0.001

    def test_deactivate_super(self) -> None:
        g = _make_game()
        g.super_timer = 50
        g._deactivate_super()
        assert g.super_timer == 0


class TestBalance:
    """Verify balance mechanics."""

    def test_left_input(self) -> None:
        g = _make_game()
        g.balance = 0.5
        g._update_balance(True, False)
        assert g.balance < 0.5

    def test_right_input(self) -> None:
        g = _make_game()
        g.balance = -0.5
        g._update_balance(False, True)
        assert g.balance > -0.5

    def test_drift_toward_center_positive(self) -> None:
        g = _make_game()
        g.balance = 0.8
        g._update_balance(False, False)
        assert g.balance < 0.8

    def test_drift_toward_center_negative(self) -> None:
        g = _make_game()
        g.balance = -0.8
        g._update_balance(False, False)
        assert g.balance > -0.8

    def test_drift_stops_at_center(self) -> None:
        g = _make_game()
        g.balance = BALANCE_DRIFT * 0.5  # Small positive
        g._update_balance(False, False)
        # Should drift to 0 and stop
        assert g.balance == 0.0

    def test_balance_clamped_upper(self) -> None:
        g = _make_game()
        g.balance = 1.5
        g._update_balance(False, False)
        assert g.balance <= 1.0

    def test_balance_clamped_lower(self) -> None:
        g = _make_game()
        g.balance = -1.5
        g._update_balance(False, False)
        assert g.balance >= -1.0

    def test_balance_at_negative_one(self) -> None:
        g = _make_game()
        g.balance = -1.0
        g._update_balance(True, False)  # Try to push further left
        assert g.balance == -1.0

    def test_balance_at_positive_one(self) -> None:
        g = _make_game()
        g.balance = 1.0
        g._update_balance(False, True)  # Try to push further right
        assert g.balance == 1.0


class TestWind:
    """Verify wind gust mechanics."""

    def test_wind_pushes_balance(self) -> None:
        g = _make_game()
        g.balance = 0.0
        g.winds.append(WindGust(direction=1, strength=0.05, duration=10, color=12))
        g._update_world(False, False)
        assert g.balance > 0.0  # Wind pushed right

    def test_wind_duration_decrements(self) -> None:
        g = _make_game()
        w = WindGust(direction=1, strength=0.02, duration=10, color=12)
        g.winds.append(w)
        g._update_world(False, False)
        assert w.duration == 9

    def test_expired_wind_removed(self) -> None:
        g = _make_game()
        w = WindGust(direction=1, strength=0.02, duration=0, color=12)
        g.winds.append(w)
        g._update_world(False, False)
        assert w not in g.winds


class TestHeat:
    """Verify heat mechanics."""

    def test_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_decay_stops_at_zero(self) -> None:
        g = _make_game()
        g.heat = HEAT_DECAY * 0.5
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_game_over(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_should_game_over_false(self) -> None:
        g = _make_game()
        g.heat = 50.0
        assert g._should_game_over() is False

    def test_should_game_over_true(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT
        assert g._should_game_over() is True


class TestSpeed:
    """Verify speed scaling."""

    def test_speed_starts_initial(self) -> None:
        g = _make_game()
        assert g.speed == SPEED_INITIAL

    def test_speed_increases_with_frames(self) -> None:
        g = _make_game()
        g.frame = 10000
        g._update_speed()
        assert g.speed > SPEED_INITIAL

    def test_speed_capped_at_max(self) -> None:
        g = _make_game()
        g.frame = 1000000
        g._update_speed()
        assert g.speed == SPEED_MAX


class TestWorldUpdate:
    """Verify core world update loop."""

    def test_distance_increases(self) -> None:
        g = _make_game()
        dist_before = g.distance
        g._update_world(False, False)
        assert g.distance > dist_before

    def test_frame_increments(self) -> None:
        g = _make_game()
        g._update_world(False, False)
        assert g.frame == 1

    def test_super_timer_decrements_in_world(self) -> None:
        g = _make_game()
        g.super_timer = 50
        g._update_world(False, False)
        assert g.super_timer == 49

    def test_gems_are_spawned(self) -> None:
        g = _make_game()
        # Advance far enough to trigger gem spawning
        for _ in range(100):
            g._update_world(False, False)
        assert len(g.gems) > 0

    def test_player_y_offset_bobs(self) -> None:
        g = _make_game()
        offsets = []
        for _ in range(10):
            g._update_world(False, False)
            offsets.append(g.player_y_offset)
        # Should vary (bobbing)
        assert len(set(offsets)) > 1


class TestParticles:
    """Verify particle system."""

    def test_spawn_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(160.0, 150.0, 8, 5)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == 8

    def test_particles_update(self) -> None:
        g = _make_game()
        g._spawn_particles(160.0, 150.0, 8, 3)
        positions_before = [(p.x, p.y, p.life) for p in g.particles]
        g._update_particles()
        for i, p in enumerate(g.particles):
            assert (p.x, p.y, p.life) != positions_before[i]

    def test_particles_expire(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_particles_with_gravity(self) -> None:
        g = _make_game()
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=8, gravity=0.15)
        g.particles = [p]
        vy_before = p.vy
        g._update_particles()
        assert p.vy > vy_before  # Gravity applied


class TestScreenShake:
    """Verify screen shake triggers on wrong-color."""

    def test_shake_on_wrong_color(self) -> None:
        g = _make_game()
        g.player_color_index = 0
        g.shake_frames = 0
        g._collect_gem(Gem(x=100.0, y=160, color_index=1))
        assert g.shake_frames > 0

    def test_shake_decays(self) -> None:
        g = _make_game()
        g.shake_frames = 5
        g._update_world(False, False)
        assert g.shake_frames == 4


class TestGemSpawning:
    """Verify gem spawning positions."""

    def test_gems_spawn_ahead(self) -> None:
        g = _make_game()
        # Set distance to trigger spawning
        g.distance = 500.0
        g.last_gem_x = 500.0
        g._spawn_gems()
        for gem in g.gems:
            # Gem world x should be ahead of current distance
            assert gem.x > g.distance

    def test_gem_has_valid_color(self) -> None:
        g = _make_game()
        g.distance = 500.0
        g.last_gem_x = 500.0
        g._spawn_gems()
        for gem in g.gems:
            assert 0 <= gem.color_index < NUM_GEM_COLORS

    def test_gem_y_near_rope(self) -> None:
        g = _make_game()
        g.distance = 500.0
        g.last_gem_x = 500.0
        g._spawn_gems()
        from main import ROPE_Y
        for gem in g.gems:
            assert abs(gem.y - ROPE_Y) <= 6  # Max offset is ±4


class TestHeatFullFlow:
    """Integration: heat builds up to game over."""

    def test_heat_full_flow(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        # Add heat close to max
        g.heat = MAX_HEAT - HEAT_PER_MISS
        g.player_color_index = 0
        # Collect wrong color → heat hits max → GAME_OVER
        g._collect_gem(Gem(x=100.0, y=160, color_index=1))
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
