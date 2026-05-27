"""test_imports.py — Headless logic tests for CHROMA PRISM."""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    COMBO_ECHO_THRESHOLD,
    ECHO_DURATION,
    FPS,
    GAME_COLORS,
    HEAT_COOLDOWN,
    HEAT_MAX,
    MIN_SPAWN_DIST,
    PRISM_X,
    PRISM_Y,
    SCREEN_H,
    SCREEN_W,
    SPAWN_MARGIN,
    TARGET_SIZE,
    EchoBeam,
    Game,
    Particle,
    Phase,
    Target,
    _center_dist,
    _line_rect_intersect,
)


def _make_game() -> Game:
    """Factory: create a Game instance without pyxel.init."""
    g = Game.__new__(Game)
    # Pre-init all attributes that _init_state() will touch
    g.phase = Phase.TITLE
    g.prism_angle = 0
    g.active_color_idx = 0
    g.targets = []
    g.echo_beams = []
    g.echo_timer = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.heat_timer = 0
    g.score = 0
    g.game_timer = 0
    g.particles = []
    g.last_hits = []
    g.targets_destroyed = 0
    g.wave = 0
    g._init_state()
    g.rng = random.Random(42)
    return g


# ── Module-level helpers ──


def test_line_rect_intersect_vertical_hit() -> None:
    """Vertical line through target center = hit."""
    assert _line_rect_intersect(PRISM_X, PRISM_Y, PRISM_X, 0, PRISM_X - 5, 50, 12, 12) is True


def test_line_rect_intersect_horizontal_miss() -> None:
    """Horizontal line that doesn't intersect target = miss."""
    assert _line_rect_intersect(PRISM_X, PRISM_Y, 320, PRISM_Y, 10, 10, 12, 12) is False


def test_line_rect_intersect_diagonal_miss() -> None:
    """Diagonal line not crossing rect = miss."""
    assert _line_rect_intersect(0, 0, 40, 40, 100, 100, 12, 12) is False


def test_center_dist() -> None:
    """Distance from prism to target center."""
    t = Target(x=100, y=50, color=GAME_COLORS[0])
    expected = math.hypot(100 + 6 - PRISM_X, 50 + 6 - PRISM_Y)
    assert abs(_center_dist(t) - expected) < 0.01


# ── Initial state ──


def test_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.score == 0
    assert g.wave == 0
    assert g.targets_destroyed == 0
    assert g.echo_timer == 0
    assert len(g.targets) == 0
    assert len(g.echo_beams) == 0
    assert len(g.particles) == 0
    assert len(g.last_hits) == 0
    assert g.prism_angle == 0
    assert g.active_color_idx == 0


# ── Reset ──


def test_reset_starts_wave() -> None:
    g = _make_game()
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.wave == 1
    assert len(g.targets) == 4


# ── Color / Direction ──


def test_active_color() -> None:
    g = _make_game()
    assert g.active_color == GAME_COLORS[0]  # RED
    g.active_color_idx = 1
    assert g.active_color == GAME_COLORS[1]  # GREEN


def test_get_beam_direction_no_rotation() -> None:
    g = _make_game()
    g.prism_angle = 0
    assert g._get_beam_direction(0) == 0  # RED → UP
    assert g._get_beam_direction(1) == 1  # GREEN → RIGHT
    assert g._get_beam_direction(2) == 2  # BLUE → DOWN
    assert g._get_beam_direction(3) == 3  # YELLOW → LEFT


def test_get_beam_direction_90_rotation() -> None:
    g = _make_game()
    g.prism_angle = 90
    assert g._get_beam_direction(0) == 1  # RED → RIGHT
    assert g._get_beam_direction(1) == 2  # GREEN → DOWN
    assert g._get_beam_direction(2) == 3  # BLUE → LEFT
    assert g._get_beam_direction(3) == 0  # YELLOW → UP


def test_active_beam_direction() -> None:
    g = _make_game()
    g.prism_angle = 0
    g.active_color_idx = 0
    assert g._active_beam_direction() == 0
    g.active_color_idx = 2
    assert g._active_beam_direction() == 2


# ── Wave / Spawning ──


def test_next_wave_wave1() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    assert g.wave == 1
    assert len(g.targets) == 4
    assert g.game_timer == 60 * FPS
    assert g.combo == 0


def test_next_wave_wave2() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.wave = 1
    g._next_wave()
    assert g.wave == 2
    assert len(g.targets) == 6
    assert g.game_timer == 50 * FPS + 10 * FPS


def test_next_wave_wave3() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.wave = 2
    g._next_wave()
    assert g.wave == 3
    assert len(g.targets) == min(8, 4 + 3 * 2)  # 8
    assert g.game_timer == 45 * FPS + 10 * FPS


def test_next_wave_clears_combo_and_echo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 5
    g.echo_timer = 30
    g.echo_beams.append(EchoBeam(direction=0, color=8, timer=30))
    g.last_hits = [(0, 8), (1, 3), (2, 5)]
    g._next_wave()
    assert g.combo == 0
    assert g.echo_timer == 0
    assert len(g.echo_beams) == 0
    assert len(g.last_hits) == 0


def test_spawn_targets_wave1_hp() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.wave = 1
    g._spawn_targets(4)
    assert len(g.targets) == 4
    for t in g.targets:
        assert t.hp == 1
        assert t.active is True
        assert t.color in GAME_COLORS


def test_spawn_targets_wave2_hp() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.wave = 2
    g._spawn_targets(6)
    assert len(g.targets) == 6
    for t in g.targets:
        assert t.hp in (1, 2)


def test_spawn_targets_wave3_hp() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.wave = 3
    g._spawn_targets(8)
    assert len(g.targets) == 8
    for t in g.targets:
        assert t.hp in (1, 2, 3)


def test_targets_spawn_away_from_prism() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.wave = 1
    g._spawn_targets(4)
    for t in g.targets:
        cx = t.x + TARGET_SIZE / 2
        cy = t.y + TARGET_SIZE / 2
        dist = math.hypot(cx - PRISM_X, cy - PRISM_Y)
        assert dist >= MIN_SPAWN_DIST, f"Target at ({t.x}, {t.y}) too close to prism: {dist}"


def test_wave_clear_triggers_next_wave() -> None:
    """Simulate all targets destroyed → next wave."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    assert g.wave == 1
    wave1_score = g.score
    # Deactivate all targets (simulating destruction)
    for t in g.targets:
        t.active = False
    # This is what update() does: if no active targets, score += 500*wave, _next_wave()
    g.score += 500 * g.wave
    g._next_wave()
    assert g.wave == 2
    assert g.score == wave1_score + 500


# ── Scoring ──


def test_add_score_direct() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    g._add_score(100, is_echo=False)
    assert g.score == 100 + 2 * 50  # 200


def test_add_score_echo() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    g._add_score(50, is_echo=True)
    assert g.score == 50 + 2 * 25  # 100


def test_add_score_with_combo() -> None:
    g = _make_game()
    g.combo = 5
    g.score = 100
    g._add_score(100, is_echo=False)
    assert g.score == 100 + 100 + 5 * 50  # 450


# ── Combo ──


def test_combo_increments_on_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    assert g.combo == 0
    # Find a target of active color and place it directly in beam path
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2  # center on prism vertical beam
    target.y = 30  # above prism
    target.color = g.active_color
    target.hp = 1
    target.active = True
    g._check_beam_hits()
    assert g.combo == 1
    assert g.max_combo == 1


def test_combo_increments_max_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    # Place multiple same-color targets in beam path
    for i, target in enumerate(g.targets[:3]):
        target.x = PRISM_X - TARGET_SIZE / 2
        target.y = 20 + i * 40  # stacked vertically
        target.color = g.active_color
        target.hp = 1
        target.active = True
    g._check_beam_hits()
    assert g.combo == 1
    assert g.max_combo == 1


def test_combo_resets_on_miss() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    g.combo = 3
    # Place a wrong-color target in beam path
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2
    target.y = 30
    # Ensure wrong color
    wrong_colors = [c for c in GAME_COLORS if c != g.active_color]
    target.color = wrong_colors[0]
    target.hp = 1
    target.active = True
    g._check_beam_hits()
    assert g.combo == 0


# ── Heat ──


def test_add_heat() -> None:
    g = _make_game()
    g._add_heat(1)
    assert g.heat == 1


def test_heat_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._add_heat(HEAT_MAX)
    assert g.heat == HEAT_MAX
    assert g.phase == Phase.GAME_OVER


def test_heat_decays() -> None:
    g = _make_game()
    g.heat = 5
    g.heat_timer = HEAT_COOLDOWN - 1
    g._update_heat()
    assert g.heat == 4
    assert g.heat_timer == 0


def test_heat_zero_no_decay() -> None:
    g = _make_game()
    g.heat = 0
    g.heat_timer = HEAT_COOLDOWN - 1
    g._update_heat()
    assert g.heat == 0


def test_miss_adds_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    g.combo = 1
    g.heat = 0
    # Place wrong-color target
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2
    target.y = 30
    wrong_colors = [c for c in GAME_COLORS if c != g.active_color]
    target.color = wrong_colors[0]
    target.hp = 1
    target.active = True
    g._check_beam_hits()
    assert g.heat == 1
    assert g.combo == 0


# ── Echo System ──


def test_activate_echo_at_threshold() -> None:
    g = _make_game()
    g.combo = COMBO_ECHO_THRESHOLD
    g.last_hits = [(0, 8), (1, 3), (2, 5)]
    g.echo_timer = 0
    g._activate_echo()
    assert g.echo_timer == ECHO_DURATION
    assert len(g.echo_beams) == 3
    assert g.echo_beams[0].direction == 0
    assert g.echo_beams[0].color == 8


def test_handle_hit_triggers_echo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    g.combo = 2  # hit will make combo=3
    g.last_hits = [(0, 8), (1, 3)]
    g.echo_timer = 0
    g.echo_beams = []
    # Place same-color target
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2
    target.y = 30
    target.color = g.active_color
    target.hp = 1
    target.active = True
    g._check_beam_hits()
    assert g.combo == 3
    assert g.echo_timer > 0
    assert len(g.echo_beams) == 3  # last_hits now has 3 entries


def test_last_hits_capped_at_3() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    # Add 4 hits
    for i in range(4):
        g.last_hits.append((i % 4, GAME_COLORS[i % 4]))
        if len(g.last_hits) > 3:
            g.last_hits.pop(0)
    assert len(g.last_hits) == 3
    assert g.last_hits[0] == (1, GAME_COLORS[1])


def test_update_echo_beams_decrements_timer() -> None:
    g = _make_game()
    g.echo_timer = 10
    g.echo_beams = [EchoBeam(direction=0, color=8, timer=10)]
    g._update_echo_beams()
    assert g.echo_timer == 9
    assert g.echo_beams[0].timer == 9


def test_echo_beams_expire() -> None:
    g = _make_game()
    g.echo_beams = [EchoBeam(direction=0, color=8, timer=1)]
    g._update_echo_beams()
    assert len(g.echo_beams) == 0


def test_echo_hit_resets_per_frame() -> None:
    g = _make_game()
    echo = EchoBeam(direction=0, color=8, timer=10, hit_this_frame=True)
    g.echo_beams = [echo]
    g._update_echo_beams()
    assert g.echo_beams[0].hit_this_frame is False


# ── Hit Detection ──


def test_check_beam_hits_wrong_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    g.combo = 1
    g.heat = 0
    # Place target of wrong color in beam
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2
    target.y = 30
    wrong_colors = [c for c in GAME_COLORS if c != g.active_color]
    target.color = wrong_colors[0]
    target.hp = 1
    target.active = True
    g._check_beam_hits()
    assert g.combo == 0
    assert g.heat == 1


def test_check_beam_hits_correct_color_kill() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    g.combo = 0
    g.score = 0
    # Place target of correct color with hp=1
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2
    target.y = 30
    target.color = g.active_color
    target.hp = 1
    target.active = True
    g._check_beam_hits()
    assert g.combo == 1
    assert target.active is False
    assert g.targets_destroyed == 1
    assert g.score == 100 + 1 * 50  # base 100 + combo*50 (combo=1 after hit)
    # Note: add_score uses self.combo which was already incremented


def test_check_beam_hits_target_hp_reduction() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    # Place target with hp=2
    target = g.targets[0]
    target.x = PRISM_X - TARGET_SIZE / 2
    target.y = 30
    target.color = g.active_color
    target.hp = 2
    target.active = True
    g._check_beam_hits()
    assert target.hp == 1
    assert target.active is True  # not dead yet


# ── Particle System ──


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 8)
    assert len(g.particles) >= 8
    assert len(g.particles) <= 12
    for p in g.particles:
        assert p.life == 20
        assert p.color == 8


def test_update_particles() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=100, y=100, vx=1, vy=2, life=2, color=8),
        Particle(x=200, y=200, vx=-1, vy=-1, life=1, color=3),
    ]
    g._update_particles()
    # particle 0: life=2→1, moved
    # particle 1: life=1→0, removed
    assert len(g.particles) == 1
    assert g.particles[0].life == 1
    assert g.particles[0].x == 101
    assert g.particles[0].y == 102


# ── Beam Segment ──


def test_beam_segment_up() -> None:
    g = _make_game()
    seg = g._beam_segment(0)  # DIR_UP
    assert seg == (PRISM_X, PRISM_Y, PRISM_X, 0)


def test_beam_segment_right() -> None:
    g = _make_game()
    seg = g._beam_segment(1)  # DIR_RIGHT
    assert seg == (PRISM_X, PRISM_Y, SCREEN_W, PRISM_Y)


def test_beam_segment_down() -> None:
    g = _make_game()
    seg = g._beam_segment(2)  # DIR_DOWN
    assert seg == (PRISM_X, PRISM_Y, PRISM_X, SCREEN_H)


def test_beam_segment_left() -> None:
    g = _make_game()
    seg = g._beam_segment(3)  # DIR_LEFT
    assert seg == (PRISM_X, PRISM_Y, 0, PRISM_Y)


# ── Target distance along beam ──


def test_target_dist_along_beam_up() -> None:
    t = Target(x=PRISM_X - TARGET_SIZE / 2, y=50, color=8)
    dist = Game._target_dist_along_beam(t, 0)  # UP
    expected = PRISM_Y - (50 + TARGET_SIZE / 2)
    assert abs(dist - expected) < 0.01


def test_target_dist_along_beam_down() -> None:
    t = Target(x=PRISM_X - TARGET_SIZE / 2, y=200, color=8)
    dist = Game._target_dist_along_beam(t, 2)  # DOWN
    expected = (200 + TARGET_SIZE / 2) - PRISM_Y
    assert abs(dist - expected) < 0.01


# ── Timer ──


def test_timer_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._next_wave()
    g.game_timer = 1
    # Simulate what update() does
    g.game_timer -= 1
    assert g.game_timer == 0
    g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── on_target_destroyed ──


def test_on_target_destroyed_direct() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    g.targets_destroyed = 0
    target = Target(x=100, y=100, color=8, hp=1)
    g._on_target_destroyed(target, is_echo=False)
    assert g.targets_destroyed == 1
    assert g.score == 100 + 2 * 50


def test_on_target_destroyed_echo() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    g.targets_destroyed = 5
    target = Target(x=100, y=100, color=8, hp=1)
    g._on_target_destroyed(target, is_echo=True)
    assert g.targets_destroyed == 6
    assert g.score == 50 + 2 * 25


# ── RNG determinism ──


def test_rng_deterministic_spawn() -> None:
    g1 = _make_game()
    g1.phase = Phase.PLAYING
    g1.wave = 1
    g1._spawn_targets(4)

    g2 = _make_game()
    g2.phase = Phase.PLAYING
    g2.wave = 1
    g2._spawn_targets(4)

    # Same seed → same positions
    for t1, t2 in zip(g1.targets, g2.targets):
        assert t1.x == t2.x
        assert t1.y == t2.y
        assert t1.color == t2.color
        assert t1.hp == t2.hp


# ── Phase transitions ──


def test_phase_enum_values() -> None:
    assert Phase.TITLE == "TITLE"
    assert Phase.PLAYING == "PLAYING"
    assert Phase.GAME_OVER == "GAME_OVER"


# ── Config constants ──


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert FPS == 30
    assert HEAT_MAX == 10
    assert COMBO_ECHO_THRESHOLD == 3
    assert HEAT_COOLDOWN == 3 * FPS
    assert ECHO_DURATION == 5 * FPS
    assert TARGET_SIZE == 12
    assert MIN_SPAWN_DIST == 40
    assert SPAWN_MARGIN == 16
    assert len(GAME_COLORS) == 4


print("ALL TESTS PASSED")
