"""test_imports.py — Headless logic tests for 074_chain_climb."""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from main import (  # noqa: E402
    BASE_SCORE,
    COLOR_INT_MAP,
    COMBO_BONUS,
    COMBO_THRESHOLD,
    GRAVITY,
    JUMP_VELOCITY,
    PARTICLE_COUNT_NORMAL,
    PARTICLE_COUNT_SYNTHESIS,
    SCREEN_H,
    SCREEN_W,
    SYNTHESIS_FRAMES,
    SYNTHESIS_JUMP_VELOCITY,
    SYNTHESIS_MULTIPLIER,
    MAX_FALL_SPEED,
    PLATFORM_COLORS,
    PLAYER_H,
    PLAYER_W,
    Game,
    Particle,
    Phase,
    Platform,
    PlatformColor,
    Player,
)


def _make_game() -> Game:
    """Create a Game instance for headless testing (bypasses pyxel.init/run)."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.player = Player(x=160.0, y=200.0, vy=0.0, width=PLAYER_W, height=PLAYER_H, on_ground=False)
    g.platforms = []
    g.particles = []
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.prev_color = None
    g.synthesis_timer = 0
    g.camera_y = 0.0
    g.scroll_speed = 0.8
    g._platform_spawn_y = 0.0
    g._frame = 0
    g.reset()
    return g


# ── Data Classes ────────────────────────────────────────────────────────


def test_platform_dataclass() -> None:
    p = Platform(x=100.0, y=200.0, width=40.0, height=8.0, color=PlatformColor.RED)
    assert p.x == 100.0
    assert p.y == 200.0
    assert p.width == 40.0
    assert p.height == 8.0
    assert p.color == PlatformColor.RED


def test_player_dataclass() -> None:
    p = Player(x=160.0, y=200.0, vy=0.0, width=12, height=16, on_ground=True)
    assert p.x == 160.0
    assert p.y == 200.0
    assert p.vy == 0.0
    assert p.on_ground is True


def test_particle_dataclass() -> None:
    p = Particle(x=5.0, y=10.0, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.life == 20
    assert p.color == 8


# ── Constants ───────────────────────────────────────────────────────────


def test_platform_colors() -> None:
    assert len(PLATFORM_COLORS) == 4
    assert PlatformColor.RED in PLATFORM_COLORS
    assert PlatformColor.GREEN in PLATFORM_COLORS
    assert PlatformColor.DARK_BLUE in PLATFORM_COLORS
    assert PlatformColor.YELLOW in PLATFORM_COLORS


def test_color_int_map() -> None:
    assert COLOR_INT_MAP[PlatformColor.RED] == 8
    assert COLOR_INT_MAP[PlatformColor.GREEN] == 3
    assert COLOR_INT_MAP[PlatformColor.DARK_BLUE] == 5
    assert COLOR_INT_MAP[PlatformColor.YELLOW] == 10


# ── Game State / reset / start ──────────────────────────────────────────


def test_reset_sets_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.prev_color is None
    assert g.synthesis_timer == 0
    assert g.camera_y == 0.0
    assert len(g.particles) == 0


def test_start_game_initializes_platforms() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert len(g.platforms) == 8
    assert g.player.x == pytest.approx(160.0)
    assert g.score == 0
    assert g.combo == 0


# ── _compute_score ──────────────────────────────────────────────────────


def test_compute_score_no_combo() -> None:
    assert Game._compute_score(0) == BASE_SCORE  # 10
    assert Game._compute_score(1) == BASE_SCORE + COMBO_BONUS  # 25


def test_compute_score_high_combo() -> None:
    assert Game._compute_score(5) == BASE_SCORE + 5 * COMBO_BONUS  # 85


# ── _apply_gravity ──────────────────────────────────────────────────────


def test_gravity_increases_vy() -> None:
    g = _make_game()
    g.player.vy = 0.0
    g.player.y = 200.0
    g._apply_gravity()
    assert g.player.vy == GRAVITY
    assert g.player.y > 200.0


def test_gravity_caps_fall_speed() -> None:
    g = _make_game()
    g.player.vy = MAX_FALL_SPEED + 1.0
    g._apply_gravity()
    assert g.player.vy == MAX_FALL_SPEED


# ── _move_player ────────────────────────────────────────────────────────


def test_move_player_right() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 200.0
    g.player.vy = 0.0
    g._move_player(2.0)
    assert g.player.x == 102.0


def test_move_player_wrap_right() -> None:
    g = _make_game()
    g.player.x = SCREEN_W + 1.0
    g._move_player(0.0)
    assert g.player.x == pytest.approx(1.0)


def test_move_player_wrap_left() -> None:
    g = _make_game()
    g.player.x = -1.0
    g._move_player(0.0)
    assert g.player.x == pytest.approx(SCREEN_W - 1.0)


# ── _check_platform_collision ───────────────────────────────────────────


def test_no_collision_when_moving_up() -> None:
    g = _make_game()
    g.player.vy = -3.0
    g.platforms = [Platform(x=160.0, y=200.0, width=40.0, height=8.0, color=PlatformColor.RED)]
    landed, color = g._check_platform_collision()
    assert landed is False
    assert color is None


def test_collision_lands_on_platform() -> None:
    g = _make_game()
    g.player.x = 160.0
    g.player.y = 192.0  # bottom at 192+16=208, platform top at 200
    g.player.vy = 8.0  # falling
    g.player.on_ground = False
    g.platforms = [Platform(x=160.0, y=200.0, width=40.0, height=8.0, color=PlatformColor.RED)]
    landed, color = g._check_platform_collision()
    assert landed is True
    assert color == PlatformColor.RED
    # Player should be placed on top of platform
    assert g.player.y == pytest.approx(200.0 - PLAYER_H)
    assert g.player.vy == JUMP_VELOCITY


def test_no_collision_when_miss_platform() -> None:
    g = _make_game()
    g.player.x = 50.0  # far from platform at x=160
    g.player.y = 192.0
    g.player.vy = 8.0
    g.platforms = [Platform(x=160.0, y=200.0, width=40.0, height=8.0, color=PlatformColor.RED)]
    landed, color = g._check_platform_collision()
    assert landed is False


# ── _handle_landing ─────────────────────────────────────────────────────


def test_handle_landing_first_landing_no_prev_color() -> None:
    g = _make_game()
    g.prev_color = None
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 1
    assert g.prev_color == PlatformColor.RED
    assert g.score == BASE_SCORE  # 10


def test_handle_landing_same_color_extends_combo() -> None:
    g = _make_game()
    g.prev_color = PlatformColor.RED
    g.combo = 1
    g.score = 0
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 2
    assert g.score == Game._compute_score(2)  # BASE + 2*BONUS = 40


def test_handle_landing_different_color_resets_combo() -> None:
    g = _make_game()
    g.prev_color = PlatformColor.RED
    g.combo = 5
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.GREEN)
    assert g.combo == 1
    assert g.prev_color == PlatformColor.GREEN
    assert g.score == BASE_SCORE


def test_handle_landing_triggers_synthesis_at_threshold() -> None:
    g = _make_game()
    g.prev_color = PlatformColor.RED
    g.combo = COMBO_THRESHOLD - 1  # 2
    g.synthesis_timer = 0
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.RED)
    assert g.combo == COMBO_THRESHOLD  # 3
    assert g.synthesis_timer == SYNTHESIS_FRAMES  # 60
    assert g.player.vy == SYNTHESIS_JUMP_VELOCITY


def test_handle_landing_during_synthesis_keeps_combo() -> None:
    g = _make_game()
    g.synthesis_timer = 30
    g.combo = 4
    g.prev_color = PlatformColor.DARK_BLUE
    g.player.x = 160.0
    g.player.y = 200.0
    score_before = g.score
    g._handle_landing(PlatformColor.DARK_BLUE)
    assert g.combo == 5
    # Score should be 3x during synthesis
    expected = Game._compute_score(5) * SYNTHESIS_MULTIPLIER
    assert g.score == score_before + expected
    assert g.player.vy == SYNTHESIS_JUMP_VELOCITY


def test_handle_landing_during_synthesis_wrong_color_no_reset() -> None:
    """During SYNTHESIS, different color still extends combo (synthesis overrides)."""
    g = _make_game()
    g.synthesis_timer = 30
    g.combo = 4
    g.prev_color = PlatformColor.DARK_BLUE
    g.player.x = 160.0
    g.player.y = 200.0
    score_before = g.score
    g._handle_landing(PlatformColor.RED)  # different color!
    assert g.combo == 5  # still extends
    assert g.score > score_before


def test_handle_landing_spawns_synthesis_particles() -> None:
    g = _make_game()
    g.synthesis_timer = 30
    g.combo = 4
    g.prev_color = PlatformColor.RED
    g.player.x = 160.0
    g.player.y = 200.0
    before = len(g.particles)
    g._handle_landing(PlatformColor.RED)
    assert len(g.particles) == before + PARTICLE_COUNT_SYNTHESIS  # 12


def test_handle_landing_spawns_normal_particles() -> None:
    g = _make_game()
    g.prev_color = None
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.GREEN)
    assert len(g.particles) == PARTICLE_COUNT_NORMAL  # 6


def test_handle_landing_tracks_max_combo() -> None:
    g = _make_game()
    g.prev_color = PlatformColor.RED
    g.combo = 7
    g.max_combo = 3
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 8
    assert g.max_combo == 8


# ── _update_camera ──────────────────────────────────────────────────────


def test_update_camera_moves_down() -> None:
    g = _make_game()
    g.scroll_speed = 1.0
    initial = g.camera_y
    g._update_camera()
    assert g.camera_y == initial + 1.0


# ── _check_fall_death ───────────────────────────────────────────────────


def test_check_fall_death_player_above_screen() -> None:
    g = _make_game()
    g.player.y = 100.0  # world y
    g.camera_y = 0.0  # screen y = 100
    assert g._check_fall_death() is False


def test_check_fall_death_player_below_screen() -> None:
    g = _make_game()
    g.player.y = SCREEN_H + 100.0  # world y
    g.camera_y = 0.0  # screen y > SCREEN_H
    assert g._check_fall_death() is True


# ── _update_scroll_speed ────────────────────────────────────────────────


def test_scroll_speed_increases_with_score() -> None:
    g = _make_game()
    g.score = 500
    g._update_scroll_speed()
    assert g.scroll_speed > 0.8  # initial


def test_scroll_speed_capped() -> None:
    g = _make_game()
    g.score = 999999
    g._update_scroll_speed()
    assert g.scroll_speed <= 2.5  # MAX_SCROLL_SPEED


# ── _update_synthesis_timer ─────────────────────────────────────────────


def test_synthesis_timer_decrements() -> None:
    g = _make_game()
    g.synthesis_timer = 30
    g._update_synthesis_timer()
    assert g.synthesis_timer == 29


def test_synthesis_timer_ends_resets_prev_color() -> None:
    g = _make_game()
    g.synthesis_timer = 1
    g.prev_color = PlatformColor.RED
    g._update_synthesis_timer()
    assert g.synthesis_timer == 0
    assert g.prev_color is None


def test_synthesis_timer_zero_does_nothing() -> None:
    g = _make_game()
    g.synthesis_timer = 0
    g.prev_color = PlatformColor.GREEN
    g._update_synthesis_timer()
    assert g.synthesis_timer == 0
    assert g.prev_color == PlatformColor.GREEN


# ── _update_particles ───────────────────────────────────────────────────


def test_update_particles_move_and_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=10, color=8)]
    g._update_particles()
    assert g.particles[0].x == 101.0
    assert g.particles[0].y == 99.0  # -1 + gravity=0.08 = -0.92
    assert g.particles[0].life == 9


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0


# ── _spawn_landing_particles ────────────────────────────────────────────


def test_spawn_landing_particles_creates_correct_count() -> None:
    g = _make_game()
    g._spawn_landing_particles(100.0, 200.0, PlatformColor.RED, 4)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == 8  # RED color int
        assert p.life >= 15


# ── Platform spawning ───────────────────────────────────────────────────


def test_spawn_platforms_adds_platforms() -> None:
    g = _make_game()
    g.platforms.clear()
    g.camera_y = 0.0
    g._platform_spawn_y = 20.0
    g._spawn_platforms()
    assert len(g.platforms) == 8


def test_spawn_platforms_removes_far_behind() -> None:
    g = _make_game()
    g.camera_y = 500.0
    g.platforms = [Platform(x=100.0, y=10.0, width=40.0, height=8.0, color=PlatformColor.RED)]
    g._platform_spawn_y = 500.0
    g._spawn_platforms()
    # Platform at y=10 with camera_y=500 → screen y = -490, should be removed
    for p in g.platforms:
        assert p.y - g.camera_y > -100  # well within buffer


# ── Phase management ────────────────────────────────────────────────────


def test_phase_enum_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Platform layout ─────────────────────────────────────────────────────


def test_platform_bounds_within_screen() -> None:
    """All platforms in initial spawn should be within screen horizontally."""
    g = _make_game()
    g._start_game()
    for p in g.platforms:
        assert p.x - p.width / 2 >= 0 - 5  # some margin
        assert p.x + p.width / 2 <= SCREEN_W + 5


def test_init_platforms_spawns_eight() -> None:
    g = _make_game()
    g._init_platforms()
    assert len(g.platforms) == 8


# ── Score/combo integration ─────────────────────────────────────────────


def test_full_combo_chain_builds_score_progressively() -> None:
    """Simulate a 5-landing same-color chain."""
    g = _make_game()
    g.player.x = 160.0
    g.player.y = 200.0
    g.score = 0
    g.combo = 0
    g.prev_color = None

    # Landing 1: RED, combo starts at 1
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 1
    assert g.score == BASE_SCORE  # first landing = BASE_SCORE only (prev_color was None)

    # Landing 2: RED, combo grows to 2
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 2
    # Score increases by BASE_SCORE + 2*BONUS = 10+30 = 40
    assert g.score == 10 + 40  # 50

    # Landing 3: RED, combo=3 triggers SYNTHESIS
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 3
    assert g.synthesis_timer == SYNTHESIS_FRAMES

    # Landing 4: RED during SYNTHESIS, combo=4, 3x score
    g._handle_landing(PlatformColor.RED)
    assert g.combo == 4
    # Score = prev + _compute_score(4)*3 = prev + (10+4*15)*3 = prev + 210

    # Landing 5: GREEN during SYNTHESIS, combo=5 (still extends)
    g._handle_landing(PlatformColor.GREEN)
    assert g.combo == 5


def test_combo_reset_on_wrong_color() -> None:
    """Wrong color resets combo to 1."""
    g = _make_game()
    g.prev_color = PlatformColor.RED
    g.combo = 5
    g.player.x = 160.0
    g.player.y = 200.0
    g._handle_landing(PlatformColor.GREEN)
    assert g.combo == 1
    assert g.prev_color == PlatformColor.GREEN


# ── Run tests via pytest ────────────────────────────────────────────────
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
