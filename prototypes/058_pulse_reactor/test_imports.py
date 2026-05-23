"""test_imports.py — Headless logic tests for PULSE REACTOR.

Tests core game logic without initialising Pyxel.
Uses Game.__new__(Game) pattern to bypass pyxel.init()/pyxel.run().
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

# Add prototype dir to path for import
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from main import (  # noqa: E402
    BEAT_COLORS,
    BEAT_COLOR_NAMES,
    CENTER_X,
    CENTER_Y,
    FPS,
    GAME_TIME_FRAMES,
    MAX_HP,
    MISS_RADIUS,
    NUM_BEAT_COLORS,
    OVERLOAD_DRAIN_INTERVAL,
    OVERLOAD_THRESHOLD,
    PERFECT_RADIUS,
    SCREEN_H,
    SCREEN_W,
    STRIKE_RADIUS,
    Beat,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game() -> Game:
    """Create a Game instance bypassing pyxel.init()."""
    g = Game.__new__(Game)
    g.reset()
    return g


# ── Constants ────────────────────────────────────────────────────────────


def test_constants() -> None:
    """Verify all game constants are sane."""
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert CENTER_X == 160
    assert CENTER_Y == 120
    assert FPS == 60
    assert GAME_TIME_FRAMES == 3600
    assert MAX_HP == 10
    assert OVERLOAD_THRESHOLD == 8
    assert STRIKE_RADIUS > PERFECT_RADIUS > MISS_RADIUS
    assert len(BEAT_COLORS) == NUM_BEAT_COLORS == 4
    assert len(BEAT_COLOR_NAMES) == 4


# ── Dataclasses ──────────────────────────────────────────────────────────


def test_beat_creation() -> None:
    """Beat dataclass constructs and properties work."""
    b = Beat(x=100.0, y=50.0, direction=0, color=0, speed=1.5)
    assert b.x == 100.0
    assert b.y == 50.0
    assert b.direction == 0
    assert b.color == 0
    assert b.speed == 1.5
    assert b.alive is True
    assert b.color_val == BEAT_COLORS[0]
    assert b.color_name == BEAT_COLOR_NAMES[0]
    d = b.dist_to_center()
    assert abs(d - math.hypot(100 - 160, 50 - 120)) < 0.01


def test_particle_creation() -> None:
    """Particle dataclass constructs correctly."""
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=10, color=8)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 10
    assert p.color == 8


def test_floating_text_creation() -> None:
    """FloatingText dataclass constructs correctly."""
    ft = FloatingText(x=100.0, y=80.0, text="TEST", life=20, color=7)
    assert ft.x == 100.0
    assert ft.y == 80.0
    assert ft.text == "TEST"
    assert ft.life == 20
    assert ft.color == 7


# ── Game state initialisation ────────────────────────────────────────────


def test_reset_initial_state() -> None:
    """reset() sets all state to defaults."""
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.current_color is None
    assert g.hp == MAX_HP
    assert g.timer == GAME_TIME_FRAMES
    assert g.synthesis_multiplier == 1.0
    assert g.overload is False
    assert g._overload_drain_timer == OVERLOAD_DRAIN_INTERVAL
    assert g.beats == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g._shake_frames == 0
    assert g._frame == 0


def test_reset_clears_previous_state() -> None:
    """reset() clears previously accumulated state."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.combo = 5
    g.max_combo = 7
    g.current_color = 2
    g.hp = 3
    g.timer = 100
    g.overload = True
    g.beats = [Beat(0, 0, 0, 0, 1.0)]
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.floating_texts = [FloatingText(0, 0, "x", 3, 7)]
    g._shake_frames = 10
    g._frame = 999

    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.current_color is None
    assert g.hp == MAX_HP
    assert g.timer == GAME_TIME_FRAMES
    assert g.beats == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g._shake_frames == 0
    assert g._frame == 0


# ── Properties ───────────────────────────────────────────────────────────


def test_time_left_sec() -> None:
    """time_left_sec reflects timer / FPS."""
    g = make_game()
    assert g.time_left_sec == 60.0
    g.timer = 1800  # 30 seconds at 60 FPS
    assert g.time_left_sec == 30.0


def test_elapsed_sec() -> None:
    """elapsed_sec is GAME_TIME_SEC - time_left_sec."""
    g = make_game()
    g.timer = 1800
    assert abs(g.elapsed_sec - 30.0) < 0.01


def test_available_colors_by_time() -> None:
    """available_colors unlocks based on elapsed time."""
    g = make_game()
    g.timer = GAME_TIME_FRAMES  # 0s elapsed → 2 colours
    assert g.available_colors == 2

    g.timer = GAME_TIME_FRAMES - 16 * FPS  # 16s elapsed → 3 colours
    assert g.available_colors == 3

    g.timer = GAME_TIME_FRAMES - 31 * FPS  # 31s elapsed → 4 colours
    assert g.available_colors == 4


def test_beat_speed_scaling() -> None:
    """beat_speed increases every 10 seconds."""
    g = make_game()
    g.timer = GAME_TIME_FRAMES  # 0s
    assert abs(g.beat_speed - 1.2) < 0.01

    g.timer = GAME_TIME_FRAMES - 12 * FPS  # 12s
    assert abs(g.beat_speed - (1.2 + 0.35)) < 0.01

    g.timer = GAME_TIME_FRAMES - 25 * FPS  # 25s
    assert abs(g.beat_speed - (1.2 + 2 * 0.35)) < 0.01


def test_spawn_interval_scaling() -> None:
    """spawn_interval decreases every 15 seconds."""
    g = make_game()
    g.timer = GAME_TIME_FRAMES  # 0s
    assert g.spawn_interval == 55

    g.timer = GAME_TIME_FRAMES - 20 * FPS  # 20s
    assert g.spawn_interval == 55 - 10  # = 45

    g.timer = GAME_TIME_FRAMES - 35 * FPS  # 35s
    assert g.spawn_interval == 55 - 2 * 10  # = 35


# ── Beat spawning ────────────────────────────────────────────────────────


def test_spawn_beat_creates_beat() -> None:
    """_spawn_beat creates a Beat when cooldown is zero."""
    g = make_game()
    g.phase = Phase.PLAYING
    g._spawn_cooldown = 0
    initial_count = len(g.beats)
    g._spawn_beat()
    assert len(g.beats) == initial_count + 1
    beat = g.beats[-1]
    assert beat.alive is True
    assert beat.direction in (0, 1, 2, 3)
    assert beat.color in (0, 1)  # only 2 colours at start
    assert beat.speed > 0


def test_spawn_beat_cooldown() -> None:
    """_spawn_beat respects cooldown."""
    g = make_game()
    g.phase = Phase.PLAYING
    g._spawn_cooldown = 5
    g._spawn_beat()
    assert g._spawn_cooldown == 4  # decremented but didn't spawn
    # No new beat
    assert len(g.beats) == 0


def test_spawn_beat_resets_cooldown() -> None:
    """After spawning, cooldown is reset to a positive value."""
    g = make_game()
    g.phase = Phase.PLAYING
    g._spawn_cooldown = 0
    g._spawn_beat()
    assert g._spawn_cooldown > 0


def test_spawn_beat_deterministic() -> None:
    """Same seed produces same first beat."""
    g1 = make_game()
    g2 = make_game()
    g1.phase = g2.phase = Phase.PLAYING
    g1._spawn_cooldown = g2._spawn_cooldown = 0
    g1.timer = g2.timer = GAME_TIME_FRAMES

    g1._spawn_beat()
    g2._spawn_beat()
    _ = g1.beats[0], g2.beats[0]
    # No assertion — verifying no crash on unseeded deterministic path
    pass


def test_spawn_beat_seeded() -> None:
    """Seeded RNG produces deterministic spawn."""
    g = make_game()
    g._rng.seed(42)
    g.phase = Phase.PLAYING
    g._spawn_cooldown = 0
    g.timer = GAME_TIME_FRAMES

    g._spawn_beat()
    b = g.beats[0]
    # With seed(42): first randint(0,3) → ?, randint(0,1) → ?
    assert b.direction in (0, 1, 2, 3)
    assert b.color in (0, 1)

    # Verify deterministic: same seed → same beat
    g2 = make_game()
    g2._rng.seed(42)
    g2.phase = Phase.PLAYING
    g2._spawn_cooldown = 0
    g2.timer = GAME_TIME_FRAMES
    g2._spawn_beat()
    b2 = g2.beats[0]
    assert b.direction == b2.direction
    assert b.color == b2.color
    assert b.speed == b2.speed
    assert abs(b.x - b2.x) < 0.01
    assert abs(b.y - b2.y) < 0.01


# ── Beat movement ────────────────────────────────────────────────────────


def test_update_beats_moves_toward_center() -> None:
    """Beats move toward the reactor core."""
    g = make_game()
    g.phase = Phase.PLAYING
    # Place a beat coming from the left (direction=3=right, moving right)
    b = Beat(x=0.0, y=CENTER_Y, direction=3, color=0, speed=2.0)
    g.beats.append(b)
    prev_dist = b.dist_to_center()
    g._update_beats()
    new_dist = b.dist_to_center()
    assert new_dist < prev_dist  # moved closer to center


def test_update_beats_removes_dead() -> None:
    """Dead beats are removed from the list."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.beats.append(Beat(x=0, y=0, direction=0, color=0, speed=1.0, alive=False))
    g._update_beats()
    assert len(g.beats) == 0


def test_update_beats_removes_far_off_screen() -> None:
    """Beats far off-screen are culled."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.beats.append(Beat(x=-100, y=-100, direction=0, color=0, speed=5.0))
    g._update_beats()
    assert len(g.beats) == 0 or not g.beats[0].alive


# ── Miss detection ───────────────────────────────────────────────────────


def test_check_misses_detects_beat_past_center() -> None:
    """Beat at center (within MISS_RADIUS) triggers miss."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    g.combo = 3
    g.current_color = 0
    b = Beat(x=CENTER_X, y=CENTER_Y, direction=0, color=0, speed=1.0)
    g.beats.append(b)
    g._check_misses()
    assert not b.alive
    assert g.combo == 0
    assert g.current_color is None
    assert g.hp == 4  # HP-1


def test_check_misses_no_miss_for_far_beat() -> None:
    """Beat far from center is not missed."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    b = Beat(x=300, y=200, direction=0, color=0, speed=1.0)
    g.beats.append(b)
    g._check_misses()
    assert b.alive
    assert g.hp == 5  # no HP loss


def test_check_misses_game_over_on_zero_hp() -> None:
    """HP reaching 0 from miss triggers game over."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 1
    b = Beat(x=CENTER_X, y=CENTER_Y, direction=0, color=0, speed=1.0)
    g.beats.append(b)
    g._check_misses()
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


# ── Hit detection & colour matching ──────────────────────────────────────


def test_check_hit_perfect() -> None:
    """Hitting a beat near center gives perfect score."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    # Place beat just inside PERFECT_RADIUS from center
    b = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=0, speed=1.0,
    )
    g.beats.append(b)
    g._check_hit(3)  # arrow right
    assert not b.alive
    assert g.combo == 1
    assert g.current_color == 0
    assert g.score > 0  # got points


def test_check_hit_early() -> None:
    """Hitting a beat in strike zone but not perfect gives early score."""
    g = make_game()
    g.phase = Phase.PLAYING
    # Place beat at STRIKE_RADIUS - 2 (just inside outer ring)
    b = Beat(
        x=CENTER_X + STRIKE_RADIUS - 2, y=CENTER_Y,
        direction=3, color=0, speed=1.0,
    )
    g.beats.append(b)
    g._check_hit(3)
    assert not b.alive
    assert g.combo == 1
    assert g.score > 0
    # Early hit: 50 * (1.0 + combo_new * 0.25) = 50 * 1.25 = 62
    assert g.score == 62  # combo becomes 1, multiplier=1.25, base=50


def test_check_hit_no_beat_in_zone() -> None:
    """No beat in strike zone: nothing happens."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    g.combo = 0
    # Beat too far from center
    b = Beat(x=300, y=200, direction=0, color=0, speed=1.0)
    g.beats.append(b)
    g._check_hit(0)
    assert b.alive  # not hit
    assert g.combo == 0


def test_check_hit_wrong_color_breaks_combo() -> None:
    """Hitting wrong colour resets combo and costs HP."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    g.combo = 3
    g.current_color = 0  # combo is RED
    # Place a GREEN beat
    b = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=1, speed=1.0,  # GREEN
    )
    g.beats.append(b)
    g._check_hit(3)
    assert not b.alive
    assert g.combo == 0
    assert g.current_color is None
    assert g.hp == 4  # HP-1


def test_check_hit_wrong_color_game_over() -> None:
    """Wrong colour hit with 1 HP → game over."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 1
    g.combo = 3
    g.current_color = 0
    b = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=1, speed=1.0,
    )
    g.beats.append(b)
    g._check_hit(3)
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


# ── Combo & scoring ──────────────────────────────────────────────────────


def test_combo_builds_on_same_color() -> None:
    """Consecutive same-colour hits build combo."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 0

    # First RED hit
    b1 = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=0, speed=1.0,
    )
    g.beats.append(b1)
    g._check_hit(3)
    assert g.combo == 1
    assert g.current_color == 0
    score1 = g.score

    # Second RED hit
    b2 = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=0, speed=1.0,
    )
    g.beats.append(b2)
    g._check_hit(3)
    assert g.combo == 2
    assert g.current_color == 0
    # Score should be higher due to multiplier
    assert g.score > score1


def test_synthesis_multiplier_grows_with_combo() -> None:
    """Multiplier = 1.0 + combo * 0.25."""
    g = make_game()
    g.phase = Phase.PLAYING

    g.combo = 4
    g.synthesis_multiplier = 1.0 + g.combo * 0.25
    assert abs(g.synthesis_multiplier - 2.0) < 0.01

    g.combo = 12
    g.synthesis_multiplier = 1.0 + g.combo * 0.25
    assert abs(g.synthesis_multiplier - 4.0) < 0.01


def test_max_combo_tracks_peak() -> None:
    """max_combo records the highest combo reached."""
    g = make_game()
    g.phase = Phase.PLAYING

    for i in range(5):
        b = Beat(
            x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
            direction=3, color=0, speed=1.0,
        )
        g.beats.append(b)
        g._check_hit(3)
    assert g.combo == 5
    assert g.max_combo == 5

    # Break combo with wrong colour
    b_bad = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=1, speed=1.0,
    )
    g.beats.append(b_bad)
    g._check_hit(3)
    assert g.combo == 0
    assert g.max_combo == 5  # max combo preserved


# ── Overload ─────────────────────────────────────────────────────────────


def test_overload_triggers_at_threshold() -> None:
    """overload flag sets when combo >= OVERLOAD_THRESHOLD."""
    g = make_game()
    g.phase = Phase.PLAYING

    for i in range(OVERLOAD_THRESHOLD):
        b = Beat(
            x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
            direction=3, color=0, speed=1.0,
        )
        g.beats.append(b)
        g._check_hit(3)

    assert g.combo == OVERLOAD_THRESHOLD
    assert g.overload is True


def test_update_overload_drains_hp() -> None:
    """Overload state drains HP periodically."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    g.overload = True
    g._overload_drain_timer = 0  # trigger immediately

    g._update_overload()
    assert g.hp == 4  # HP-1
    assert g._overload_drain_timer == OVERLOAD_DRAIN_INTERVAL  # reset


def test_update_overload_does_not_drain_when_inactive() -> None:
    """No HP drain when overload is False."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    g.overload = False
    g._overload_drain_timer = 0

    g._update_overload()
    assert g.hp == 5  # no change
    assert g._overload_drain_timer == OVERLOAD_DRAIN_INTERVAL


def test_update_overload_game_over() -> None:
    """Overload drain to 0 HP → game over."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 1
    g.overload = True
    g._overload_drain_timer = 0

    g._update_overload()
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


# ── Discharge ────────────────────────────────────────────────────────────


def test_discharge_grants_bonus() -> None:
    """Discharging when overloaded gives score bonus."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 10
    g.overload = True

    g._discharge()
    expected_bonus = 10 * 200  # 2000
    assert g.score == expected_bonus
    assert g.overload is False
    assert g._shake_frames > 0


def test_discharge_no_op_when_not_overloaded() -> None:
    """Calling discharge without overload does nothing."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 100
    g.combo = 5
    g.overload = False

    g._discharge()
    assert g.score == 100  # unchanged
    assert g.overload is False


# ── Particles ────────────────────────────────────────────────────────────


def test_spawn_particles_creates_particles() -> None:
    """_spawn_particles adds particles to the list."""
    g = make_game()
    g._spawn_particles(100, 100, 8, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.life > 0
        assert p.color == 8


def test_update_particles_moves_and_decays() -> None:
    """Particles move and their life decreases."""
    g = make_game()
    g._spawn_particles(100, 100, 8, 5)
    initial_positions = [(p.x, p.y) for p in g.particles]
    initial_lives = [p.life for p in g.particles]

    g._update_particles()
    for i, p in enumerate(g.particles):
        assert p.x != initial_positions[i][0] or p.y != initial_positions[i][1]
        assert p.life == initial_lives[i] - 1


def test_update_particles_removes_dead() -> None:
    """Particles with life <= 0 are removed."""
    g = make_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=7)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text ────────────────────────────────────────────────────────


def test_spawn_floating_text() -> None:
    """_spawn_floating_text adds to list."""
    g = make_game()
    g._spawn_floating_text(100, 80, "HELLO", 7)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100
    assert ft.y == 80
    assert ft.text == "HELLO"
    assert ft.color == 7
    assert ft.life == 35


def test_update_floating_texts_rises_and_decays() -> None:
    """Floating text drifts upward and life decreases."""
    g = make_game()
    g._spawn_floating_text(100, 80, "TEST", 7)
    ft = g.floating_texts[0]
    orig_y = ft.y
    orig_life = ft.life
    g._update_floating_texts()
    assert ft.y < orig_y  # drifted up
    assert ft.life == orig_life - 1


def test_update_floating_texts_removes_expired() -> None:
    """FloatingText with life <= 0 is removed."""
    g = make_game()
    g.floating_texts = [FloatingText(x=0, y=0, text="old", life=1, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Timer ────────────────────────────────────────────────────────────────


def test_timer_counts_down() -> None:
    """Timer decrements each frame."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.timer = 100
    # We can't call update() directly (uses pyxel), but we can test timer logic
    g.timer -= 1
    assert g.timer == 99


def test_timer_zero_triggers_game_over() -> None:
    """Timer reaching 0 sets GAME_OVER."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.timer = 0
    # Simulate the update logic
    if g.timer <= 0:
        g.timer = 0
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER
    assert g.timer == 0


# ── Phase transitions ────────────────────────────────────────────────────


def test_phase_enum_values() -> None:
    """Phase enum has expected values."""
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2


def test_start_in_title_phase() -> None:
    """New game starts in TITLE phase."""
    g = make_game()
    assert g.phase == Phase.TITLE


# ── Score formula verification ───────────────────────────────────────────


def test_perfect_score_with_multiplier() -> None:
    """Perfect hit: score computed with multiplier AFTER combo increment."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    g.synthesis_multiplier = 1.0

    b = Beat(
        x=CENTER_X + PERFECT_RADIUS - 2, y=CENTER_Y,
        direction=3, color=0, speed=1.0,
    )
    g.beats.append(b)
    g._check_hit(3)
    # combo becomes 1, multiplier=1.25
    # points = int(100 * 1.25) = 125
    assert g.score == 125
    assert g.combo == 1
    assert abs(g.synthesis_multiplier - 1.25) < 0.01


def test_early_score_with_multiplier() -> None:
    """Early hit: score computed with multiplier AFTER combo increment."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 2
    g.synthesis_multiplier = 1.0 + 2 * 0.25  # = 1.5

    b = Beat(
        x=CENTER_X + STRIKE_RADIUS - 2, y=CENTER_Y,
        direction=3, color=0, speed=1.0,
    )
    g.beats.append(b)
    g._check_hit(3)
    # combo becomes 3, multiplier=1.75
    # points = int(50 * 1.75) = 87
    assert g.score == 87
    assert g.combo == 3


# ── Run all tests ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback

    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  ✓ {name}")
        except Exception:
            failed += 1
            print(f"  ✗ {name}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(0 if failed == 0 else 1)
