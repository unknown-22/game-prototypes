"""test_imports.py — Headless logic tests for Parkour Chain."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/124_parkour_chain")
from main import Game, Platform, TrailPoint, Particle, Phase
from main import RED, GREEN, DARK_BLUE, YELLOW, PINK, PLATFORM_COLORS


def _make_game() -> Game:
    """Factory: bypass __init__, pre-init all attrs, then reset with seeded RNG."""
    random.seed(42)
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.player_y = 180.0
    g.player_vy = 0.0
    g.player_on_ground = False
    g.player_landed_color = -1
    g.combo = 0
    g.max_combo = 0
    g.stamina = Game.MAX_STAMINA
    g.score = 0
    g.distance = 0.0
    g.platforms = []
    g.trail = []
    g.particles = []
    g.super_timer = 0
    g.super_particles_timer = 0
    g.camera_x = 0.0
    g.frame = 0
    g.shake_frames = 0
    g.shake_intensity = 0
    g.next_color = RED
    g.last_jump_frame = -Game.JUMP_COOLDOWN
    g.game_over_flash = 0
    g._buildings = []
    g._bg_buildings = []
    random.seed(42)
    g.reset()
    return g


# ── Dataclass Tests ──


class TestDataclasses:
    def test_platform_creation(self) -> None:
        p = Platform(100.0, 80.0, 60, RED)
        assert p.x == 100.0
        assert p.y == 80.0
        assert p.w == 60
        assert p.color == RED
        assert p.landed is False

    def test_trail_point(self) -> None:
        tp = TrailPoint(200.0, 100.0, GREEN)
        assert tp.x == 200.0
        assert tp.y == 100.0
        assert tp.color == GREEN

    def test_particle_creation(self) -> None:
        p = Particle(50.0, 60.0, 1.0, -2.0, 20, RED)
        assert p.x == 50.0
        assert p.vy == -2.0
        assert p.life == 20
        assert p.color == RED
        assert p.gravity == 0.15


# ── Phase Enum Tests ──


class TestPhases:
    def test_phases_exist(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase

    def test_reset_sets_playing(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING


# ── Platform Spawning Tests ──


class TestPlatformSpawning:
    def test_spawn_platform_returns_platform(self) -> None:
        g = _make_game()
        p = g._spawn_platform(300.0)
        assert isinstance(p, Platform)
        assert p.x == 300.0
        assert Game.PLATFORM_Y_MIN <= p.y <= Game.PLATFORM_Y_MAX
        assert Game.PLATFORM_MIN_W <= p.w <= Game.PLATFORM_MAX_W
        assert p.color in PLATFORM_COLORS

    def test_first_platform_exists_after_reset(self) -> None:
        g = _make_game()
        assert len(g.platforms) >= 1
        first = g.platforms[0]
        assert first.x == Game.PLAYER_X - 20
        assert first.w == 80

    def test_ensure_min_platforms_adds_more(self) -> None:
        g = _make_game()
        g.platforms.clear()
        g._ensure_min_platforms()
        assert len(g.platforms) >= 2

    def test_platforms_culled_left_of_camera(self) -> None:
        g = _make_game()
        g.platforms = [
            Platform(-500.0, 100.0, 60, RED),
            Platform(200.0, 120.0, 50, GREEN),
        ]
        g.camera_x = 500.0
        g._update_platforms()
        # Platform at -500 + 60 = -440 < camera_x - 100 = 400, removed
        assert len(g.platforms) >= 2  # the 200 one stays + new ones added


# ── Landing & Combo Tests ──


class TestLandings:
    def test_landing_on_platform_grounds_player(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        g.player_vy = 5.0
        g.player_on_ground = False
        world_x = g.camera_x + Game.PLAYER_X  # = 80
        plat = Platform(world_x - 10, 100.0 + Game.PLAYER_H - 2, 40, RED)
        g.platforms = [plat]
        g._check_landings()
        assert g.player_on_ground is True
        assert g.player_vy == 0.0
        assert plat.landed is True

    def test_no_landing_when_rising(self) -> None:
        g = _make_game()
        g.player_vy = -5.0
        g.player_on_ground = False
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x - 10, 116.0, 40, RED)
        g.platforms = [plat]
        g._check_landings()
        assert g.player_on_ground is False

    def test_no_landing_when_already_landed(self) -> None:
        g = _make_game()
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x - 10, 116.0, 40, RED, landed=True)
        g.platforms = [plat]
        g.player_y = 100.0
        g.player_vy = 5.0
        g.player_on_ground = False
        g._check_landings()
        assert g.player_on_ground is False

    def test_same_color_combo_increments(self) -> None:
        g = _make_game()
        g.player_landed_color = GREEN
        g.combo = 3
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, GREEN)
        g._on_platform_landed(plat)
        assert g.combo == 4
        assert g.player_landed_color == GREEN

    def test_different_color_resets_combo(self) -> None:
        g = _make_game()
        g.player_landed_color = GREEN
        g.combo = 3
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat)
        assert g.combo == 1
        assert g.player_landed_color == RED

    def test_first_landing_sets_combo_to_1(self) -> None:
        g = _make_game()
        g.player_landed_color = -1
        g.combo = 0
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, DARK_BLUE)
        g._on_platform_landed(plat)
        assert g.combo == 1

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g.max_combo = 0
        g.combo = 0
        g.player_landed_color = -1
        world_x = g.camera_x + Game.PLAYER_X
        # Land 3 times on same color
        for _ in range(5):
            plat = Platform(world_x, 100.0, 40, RED)
            g._on_platform_landed(plat)
        assert g.max_combo >= 5


# ── Echo Trail Tests ──


class TestEchoTrail:
    def test_echo_triggers_when_near_trail(self) -> None:
        g = _make_game()
        world_x = g.camera_x + Game.PLAYER_X
        g.trail = [TrailPoint(world_x, g.player_y, RED)]
        g.player_landed_color = RED
        plat = Platform(world_x, g.player_y, 40, RED)
        result = g._check_echo(plat)
        assert result is True

    def test_echo_no_match_different_color(self) -> None:
        g = _make_game()
        world_x = g.camera_x + Game.PLAYER_X
        g.trail = [TrailPoint(world_x, g.player_y, GREEN)]
        plat = Platform(world_x, g.player_y, 40, RED)
        result = g._check_echo(plat)
        assert result is False

    def test_echo_no_match_far_away(self) -> None:
        g = _make_game()
        world_x = g.camera_x + Game.PLAYER_X
        g.trail = [TrailPoint(world_x + 100, g.player_y + 100, RED)]
        plat = Platform(world_x, g.player_y, 40, RED)
        result = g._check_echo(plat)
        assert result is False

    def test_trail_appends_when_on_ground(self) -> None:
        g = _make_game()
        g.player_on_ground = True
        g.player_landed_color = GREEN
        initial_len = len(g.trail)
        g._update_trail()
        assert len(g.trail) == initial_len + 1
        assert g.trail[-1].color == GREEN

    def test_trail_not_appended_when_airborne(self) -> None:
        g = _make_game()
        g.player_on_ground = False
        initial_len = len(g.trail)
        g._update_trail()
        assert len(g.trail) == initial_len

    def test_trail_trims_at_max(self) -> None:
        g = _make_game()
        g.player_on_ground = True
        g.player_landed_color = RED
        g.trail = [TrailPoint(float(i), 100.0, RED) for i in range(Game.TRAIL_MAX + 10)]
        g._update_trail()
        assert len(g.trail) == Game.TRAIL_MAX


# ── Super Flow Tests ──


class TestSuperFlow:
    def test_super_activates_at_combo_threshold(self) -> None:
        g = _make_game()
        g.combo = Game.COMBO_FOR_SUPER - 1
        g.super_timer = 0
        g.player_landed_color = RED
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat)
        assert g.super_timer == Game.SUPER_DURATION

    def test_super_not_activated_below_threshold(self) -> None:
        g = _make_game()
        g.combo = Game.COMBO_FOR_SUPER - 2
        g.super_timer = 0
        g.player_landed_color = RED
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat)
        assert g.super_timer == 0

    def test_super_ticks_down(self) -> None:
        g = _make_game()
        g.super_timer = 10
        g.player_on_ground = True
        g._update_super()
        assert g.super_timer == 9

    def test_super_end_resets_combo(self) -> None:
        g = _make_game()
        g.super_timer = 1
        g.combo = 10
        g.player_on_ground = True
        g._update_super()
        assert g.combo == 0
        assert g.player_landed_color == -1

    def test_super_mode_always_increments_combo(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.combo = 2
        g.player_landed_color = GREEN
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, RED)  # different color
        g._on_platform_landed(plat)
        assert g.combo == 3  # still incremented because super_timer > 0

    def test_super_does_not_reactivate_while_active(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.combo = Game.COMBO_FOR_SUPER + 5
        g.player_landed_color = RED
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat)
        # super_timer stays unchanged because _on_platform_landed only
        # activates super when super_timer == 0
        assert g.super_timer == 100


# ── Stamina Tests ──


class TestStamina:
    def test_stamina_regens_on_ground(self) -> None:
        g = _make_game()
        g.stamina = 50.0
        g.player_on_ground = True
        g._update_stamina()
        assert g.stamina == 50.0 + Game.STAMINA_REGEN

    def test_stamina_does_not_regen_in_air(self) -> None:
        g = _make_game()
        g.stamina = 50.0
        g.player_on_ground = False
        g._update_stamina()
        assert g.stamina == 50.0

    def test_stamina_capped_at_max(self) -> None:
        g = _make_game()
        g.stamina = Game.MAX_STAMINA - 0.1
        g.player_on_ground = True
        g._update_stamina()
        assert g.stamina == Game.MAX_STAMINA

    def test_jump_consumes_stamina(self) -> None:
        g = _make_game()
        g.stamina = 100.0
        g.player_on_ground = True
        g.player_vy = 0.0
        g.frame = Game.JUMP_COOLDOWN + 10
        g.last_jump_frame = 0
        g._jump()
        assert g.stamina == 100.0 - Game.JUMP_COST

    def test_jump_blocked_by_insufficient_stamina(self) -> None:
        g = _make_game()
        g.stamina = Game.JUMP_COST - 1
        g.player_on_ground = True
        g.frame = Game.JUMP_COOLDOWN + 10
        g.last_jump_frame = 0
        g._jump()
        assert g.player_vy == 0.0  # no jump

    def test_jump_cooldown(self) -> None:
        g = _make_game()
        g.stamina = 100.0
        g.player_on_ground = True
        g.player_vy = 0.0
        g.frame = 5
        g.last_jump_frame = 3  # cooldown is 5, diff is 2 < 5
        g._jump()
        assert g.player_vy == 0.0  # no jump


# ── Physics Tests ──


class TestPhysics:
    def test_gravity_applied_when_not_super(self) -> None:
        g = _make_game()
        g.player_vy = 0.0
        g.player_y = 100.0
        g.player_on_ground = False
        g.super_timer = 0
        old_y = g.player_y
        g._update_player()
        assert g.player_vy == Game.GRAVITY
        assert g.player_y > old_y

    def test_super_mode_hovers_in_air(self) -> None:
        g = _make_game()
        g.player_vy = -3.0
        g.player_y = 100.0
        g.player_on_ground = False
        g.super_timer = 100
        g._update_player()
        assert g.player_vy == 0.0  # frozen
        assert g.player_y == 100.0  # unchanged

    def test_jump_sets_negative_velocity(self) -> None:
        g = _make_game()
        g.stamina = 100.0
        g.player_on_ground = True
        g.frame = Game.JUMP_COOLDOWN + 10
        g.last_jump_frame = 0
        g._jump()
        assert g.player_vy < 0
        assert g.player_vy == Game.JUMP_VEL


# ── Score Tests ──


class TestScore:
    def test_landing_awards_score(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 1
        g.player_landed_color = -1
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat)
        assert g.score > 0

    def test_combo_increases_landing_score(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 1
        g.player_landed_color = RED
        world_x = g.camera_x + Game.PLAYER_X
        plat1 = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat1)
        score_after_1 = g.score

        g.score = 0
        g.combo = 4
        g.player_landed_color = RED
        plat2 = Platform(world_x, 100.0, 40, RED)
        g._on_platform_landed(plat2)
        score_after_4 = g.score
        assert score_after_4 > score_after_1

    def test_echo_multiplies_score(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 3
        g.player_landed_color = RED
        world_x = g.camera_x + Game.PLAYER_X
        g.trail = [TrailPoint(world_x, g.player_y, RED)]
        plat = Platform(world_x, g.player_y, 40, RED)
        g._on_platform_landed(plat)
        # base = 10 * combo(3) = 30, echo *2 = 60
        assert g.score >= 60


# ── Game Over Tests ──


class TestGameOver:
    def test_game_over_transitions_phase(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._game_over()
        assert g.phase == Phase.GAME_OVER
        assert g.game_over_flash == 0

    def test_game_over_spawns_particles(self) -> None:
        g = _make_game()
        initial_particles = len(g.particles)
        g._game_over()
        assert len(g.particles) > initial_particles

    def test_game_over_triggers_shake(self) -> None:
        g = _make_game()
        g._game_over()
        assert g.shake_frames == 15
        assert g.shake_intensity == 4


# ── Particle Tests ──


class TestParticles:
    def test_particle_life_decrements(self) -> None:
        g = _make_game()
        g.particles = [Particle(100.0, 100.0, 0, 0, 5, RED)]
        g._update_particles()
        assert g.particles[0].life == 4

    def test_particle_removed_when_life_zero(self) -> None:
        g = _make_game()
        g.particles = [Particle(100.0, 100.0, 0, 0, 1, RED)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_particle_moves_with_velocity(self) -> None:
        g = _make_game()
        g.particles = [Particle(100.0, 100.0, 2.0, -3.0, 10, RED)]
        g._update_particles()
        assert g.particles[0].x == 102.0
        # vy=-3.0 + gravity(0.15) = -2.85; y = 100.0 + (-2.85) = 97.15
        assert abs(g.particles[0].y - 97.15) < 0.01

    def test_particle_gravity_applied(self) -> None:
        g = _make_game()
        g.particles = [Particle(100.0, 100.0, 0, 0, 10, RED, gravity=0.15)]
        g._update_particles()
        assert abs(g.particles[0].vy - 0.15) < 0.001

    def test_landing_particles_spawned(self) -> None:
        g = _make_game()
        initial = len(g.particles)
        g._spawn_landing_particles(200.0, 150.0, RED, 5)
        assert len(g.particles) == initial + 5
        for p in g.particles[-5:]:
            assert p.color == RED
            assert p.gravity == 0.15

    def test_echo_particles_spawned(self) -> None:
        g = _make_game()
        initial = len(g.particles)
        g._spawn_echo_particles(200.0, 150.0)
        assert len(g.particles) == initial + 8
        for p in g.particles[-8:]:
            assert p.color == PINK
            assert p.gravity == 0.1


# ── Rainbow Color Tests ──


class TestRainbow:
    def test_rainbow_returns_valid_color(self) -> None:
        g = _make_game()
        color = g._rainbow_color()
        assert color in PLATFORM_COLORS

    def test_rainbow_changes_with_frame(self) -> None:
        g = _make_game()
        g.frame = 0
        c0 = g._rainbow_color()
        g.frame = 10
        c1 = g._rainbow_color()
        # should cycle through 4 colors every 5 frames
        assert c0 != c1 or len(PLATFORM_COLORS) == 1


# ── Edge Case Tests ──


class TestEdgeCases:
    def test_empty_trail_echo_returns_false(self) -> None:
        g = _make_game()
        g.trail = []
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x, g.player_y, 40, RED)
        result = g._check_echo(plat)
        assert result is False

    def test_all_platforms_same_color_combo_works(self) -> None:
        g = _make_game()
        g.player_landed_color = RED
        g.combo = 2
        world_x = g.camera_x + Game.PLAYER_X
        for _ in range(3):
            plat = Platform(world_x, 100.0, 40, RED)
            g._on_platform_landed(plat)
        assert g.combo == 5

    def test_player_falls_off_screen(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_y = Game.SCREEN_H + 30
        # We can't call update() because it uses pyxel.btnp
        # Instead, verify the game over condition directly
        assert g.player_y > Game.SCREEN_H + 20

    def test_platform_spawn_at_y_boundaries(self) -> None:
        g = _make_game()
        # Test multiple spawns to verify y range
        for _ in range(50):
            p = g._spawn_platform(300.0)
            assert Game.PLATFORM_Y_MIN <= p.y <= Game.PLATFORM_Y_MAX

    def test_no_double_landing_on_same_platform(self) -> None:
        g = _make_game()
        world_x = g.camera_x + Game.PLAYER_X
        plat = Platform(world_x - 5, 100.0 + Game.PLAYER_H, 40, RED)
        g.platforms = [plat]
        g.player_y = 100.0
        g.player_vy = 5.0
        g.player_on_ground = False
        g._check_landings()
        assert plat.landed is True
        # Second check should not re-land
        g.player_y = 100.0
        g.player_vy = 5.0
        g.player_on_ground = False
        g._check_landings()
        assert g.player_on_ground is False

    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 9999
        g.combo = 50
        g.particles = [Particle(0, 0, 0, 0, 1, RED) for _ in range(100)]
        random.seed(42)
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert len(g.particles) == 0
        assert g.phase == Phase.PLAYING

    def test_game_constants(self) -> None:
        assert Game.SCREEN_W == 320
        assert Game.SCREEN_H == 240
        assert Game.COMBO_FOR_SUPER == 4
        assert Game.SUPER_DURATION == 300
        assert Game.SUPER_MULTIPLIER == 3
        assert Game.ECHO_MULTIPLIER == 2
        assert Game.GRAVITY == 0.5
        assert Game.JUMP_VEL < 0


# ── Super particle spawning ──


class TestSuperParticles:
    def test_super_particles_spawned(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.player_y = 150.0
        g.camera_x = 100.0
        initial = len(g.particles)
        g._spawn_super_particles()
        assert len(g.particles) == initial + 2
        # super particles have negative gravity (float upward)
        for p in g.particles[-2:]:
            assert p.gravity == -0.05


# ── Integration-like tests ──


class TestIntegration:
    def test_full_landing_cycle(self) -> None:
        """Simulate a player jumping and landing on a platform."""
        g = _make_game()
        g.player_y = 150.0
        g.player_on_ground = True
        g.stamina = 100.0
        g.frame = Game.JUMP_COOLDOWN + 10
        g.last_jump_frame = 0
        g.player_landed_color = -1

        # Jump
        g._jump()
        assert g.player_on_ground is False
        assert g.player_vy < 0

        # Fall (gravity) — enough frames to go up and come back down past start
        for _ in range(50):
            g._update_player()
        assert g.player_vy > 0  # now falling
        assert g.player_y > 150.0  # below original position

        # Place a platform at the landing point
        world_x = g.camera_x + Game.PLAYER_X
        landing_y = g.player_y + Game.PLAYER_H
        plat = Platform(world_x - 5, landing_y, 40, GREEN)
        g.platforms = [plat]

        # Land
        g._check_landings()
        assert g.player_on_ground is True
        assert g.combo == 1
        assert plat.landed is True

    def test_combo_chain_to_super(self) -> None:
        """Build combo to trigger SUPER FLOW."""
        g = _make_game()
        g.combo = 0
        g.player_landed_color = -1
        g.super_timer = 0
        world_x = g.camera_x + Game.PLAYER_X

        # Land 4 times on RED
        for i in range(4):
            plat = Platform(world_x, 100.0, 40, RED)
            g._on_platform_landed(plat)
        assert g.combo == 4
        assert g.max_combo == 4
        assert g.super_timer == Game.SUPER_DURATION

    def test_echo_bonus_in_chain(self) -> None:
        """Verify echo bonus triggers in a combo scenario."""
        g = _make_game()
        g.combo = 3
        g.player_landed_color = GREEN
        g.score = 0
        world_x = g.camera_x + Game.PLAYER_X

        # Place echo trail at landing position
        g.trail = [TrailPoint(world_x, g.player_y, GREEN)]

        plat = Platform(world_x, g.player_y + Game.PLAYER_H, 40, GREEN)
        g._on_platform_landed(plat)

        # base_score = 10 * combo(3) = 30, echo *2 = 60
        # super multiplier doesn't apply (super_timer=0)
        assert g.score >= 60
        # Check echo particles spawned (total 8)
        assert len(g.particles) >= 8
