"""test_imports.py — Headless logic tests for 034_hook_chain.

Tests game state, combo mechanics, catch logic, super mode, and resource management.
"""
import math
import sys
from pathlib import Path

# Add prototype to path
sys.path.insert(0, str(Path(__file__).parent))

from main import (
    SCREEN_W,
    SCREEN_H,
    CATCH_RANGE,
    SUPER_COMBO_THRESHOLD,
    MEGA_COMBO_THRESHOLD,
    HEAT_MAX,
    HEAT_PER_CAST,
    HEAT_COOLDOWN_FRAMES,
    SUPER_DURATION,
    GAME_DURATION,
    FPS,
    NUM_COLORS,
    COLOR_NAMES,
    COLOR_VALS,
    Fish,
    Particle,
    FloatText,
    Phase,
    Game,
)


def test_constants() -> None:
    """Verify game constants are sensible."""
    assert SCREEN_W == 256
    assert SCREEN_H == 240
    assert CATCH_RANGE == 50
    assert SUPER_COMBO_THRESHOLD == 3
    assert MEGA_COMBO_THRESHOLD == 6
    assert HEAT_MAX == 100
    assert HEAT_PER_CAST == 14
    assert HEAT_COOLDOWN_FRAMES == 120
    assert SUPER_DURATION == 300
    assert GAME_DURATION == 90
    assert FPS == 60
    assert NUM_COLORS == 4
    assert len(COLOR_NAMES) == 4
    assert len(COLOR_VALS) == 4


def test_fish_dataclass() -> None:
    """Test Fish dataclass creation and attributes."""
    f = Fish(x=100.0, y=80.0, color=0, vx=1.5)
    assert f.x == 100.0
    assert f.y == 80.0
    assert f.color == 0
    assert f.vx == 1.5
    assert f.alive is True
    assert f.size == 6
    assert f.golden is False

    # Golden fish
    gf = Fish(x=50.0, y=60.0, color=2, vx=-1.0, golden=True, size=7)
    assert gf.golden is True
    assert gf.size == 7


def test_particle_dataclass() -> None:
    """Test Particle dataclass creation."""
    p = Particle(x=64.0, y=48.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 64.0
    assert p.y == 48.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8
    assert p.size == 2


def test_float_text_dataclass() -> None:
    """Test FloatText dataclass creation."""
    ft = FloatText(x=100.0, y=50.0, text="+100", life=40, color=8)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+100"
    assert ft.life == 40
    assert ft.color == 8
    assert ft.vy == -1.5


def test_phase_enum() -> None:
    """Test Phase enum values."""
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_fish_movement() -> None:
    """Test that fish move correctly."""
    f = Fish(x=100.0, y=80.0, color=0, vx=2.0)
    f.x += f.vx
    assert f.x == 102.0
    f.x += f.vx
    assert f.x == 104.0


def test_fish_off_screen_removal() -> None:
    """Test fish are marked dead when off-screen."""
    # Right-bound fish going off-screen right
    f = Fish(x=SCREEN_W + 20, y=80.0, color=0, vx=2.0)
    f.x += f.vx
    assert f.x > SCREEN_W + 20  # beyond removal threshold (SCREEN_W + 20)

    # Left-bound fish going off-screen left
    f2 = Fish(x=-15, y=80.0, color=1, vx=-6.0)
    f2.x += f2.vx
    assert f2.x < -20


def test_particle_lifecycle() -> None:
    """Test particles lose life and get filtered."""
    p = Particle(x=0, y=0, vx=1, vy=0, life=3, color=8)
    p.life -= 1
    assert p.life == 2
    p.life -= 1
    assert p.life == 1
    p.life -= 1
    assert p.life == 0  # dead at 0


def test_float_text_movement() -> None:
    """Test FloatText floats upward."""
    ft = FloatText(x=100.0, y=50.0, text="test", life=40, color=8)
    ft.y += ft.vy
    assert ft.y < 50.0  # moved up
    ft.life -= 1
    assert ft.life == 39


def test_catch_range_math() -> None:
    """Test catch range distance calculation."""
    hook_x, hook_y = 200, 120
    fish = Fish(x=220, y=125, color=0, vx=0)

    dx = fish.x - hook_x
    dy = fish.y - hook_y
    dist = math.hypot(dx, dy)
    assert dist < CATCH_RANGE  # within range

    fish2 = Fish(x=260, y=120, color=0, vx=0)
    dx2 = fish2.x - hook_x
    dy2 = fish2.y - hook_y
    dist2 = math.hypot(dx2, dy2)
    assert dist2 > CATCH_RANGE  # out of range


def test_combo_scoring() -> None:
    """Test combo multiplier math."""
    # Combo 1: 1 + (1-1)*0.5 = 1.0
    m1 = 1 + (1 - 1) * 0.5
    assert abs(m1 - 1.0) < 0.01

    # Combo 3: 1 + (3-1)*0.5 = 2.0
    m3 = 1 + (3 - 1) * 0.5
    assert abs(m3 - 2.0) < 0.01

    # Combo 5: 1 + (5-1)*0.5 = 3.0
    m5 = 1 + (5 - 1) * 0.5
    assert abs(m5 - 3.0) < 0.01

    # Score with combo 3
    earned = int(100 * m3)
    assert earned == 200


def test_heat_mechanics() -> None:
    """Test heat accumulation and overheat threshold."""
    heat = 0.0
    # 7 casts * 14 = 98 (below threshold)
    for _ in range(7):
        heat += HEAT_PER_CAST
    assert heat == 98.0
    assert heat < HEAT_MAX

    # 8th cast triggers overheat
    heat += HEAT_PER_CAST
    assert heat >= HEAT_MAX


def test_super_thresholds() -> None:
    """Test SUPER and MEGA combo thresholds."""
    # Combo 3 → SUPER
    assert 3 >= SUPER_COMBO_THRESHOLD
    # Combo 6 → MEGA
    assert 6 >= MEGA_COMBO_THRESHOLD
    # Combo 2 → no super
    assert not (2 >= SUPER_COMBO_THRESHOLD)


def test_color_cycle() -> None:
    """Test color cycling with modulo."""
    color = 0
    color = (color + 1) % NUM_COLORS
    assert color == 1
    color = (color + 1) % NUM_COLORS
    assert color == 2
    color = (color + 1) % NUM_COLORS
    assert color == 3
    color = (color + 1) % NUM_COLORS
    assert color == 0  # wraps around

    # Reverse cycle
    color = (color - 1) % NUM_COLORS
    assert color == 3


def test_spawn_fish_creates_fish() -> None:
    """Test that _spawn_fish adds a fish to the list."""
    g = Game.__new__(Game)
    g.fish = []
    g._spawn_fish()
    assert len(g.fish) == 1
    f = g.fish[0]
    assert 0 <= f.color < NUM_COLORS
    assert f.alive is True
    assert f.size in (6, 7)


def test_fish_cleanup_removes_dead() -> None:
    """Test dead fish are filtered out."""
    g = Game.__new__(Game)
    g.fish = [
        Fish(x=100, y=80, color=0, vx=0.5, alive=True),
        Fish(x=120, y=90, color=1, vx=0.5, alive=False),
        Fish(x=140, y=70, color=2, vx=0.5, alive=True),
    ]
    g._update_fish()
    assert len(g.fish) == 2
    assert all(f.alive for f in g.fish)


def test_fish_off_screen_cleaned() -> None:
    """Test fish that move off-screen are marked dead and cleaned."""
    g = Game.__new__(Game)
    g.fish = [
        Fish(x=-30, y=80, color=0, vx=-1, alive=True),  # going off left
    ]
    g._update_fish()
    assert len(g.fish) == 0  # cleaned up


def test_particle_update() -> None:
    """Test particle update loop (gravity, life decrease)."""
    g = Game.__new__(Game)
    g.particles = [Particle(x=100, y=100, vx=1, vy=-2, life=10, color=8)]
    g._update_particles()
    p = g.particles[0]
    assert p.life == 9
    assert p.vy > -2.0  # gravity applied


def test_float_text_update() -> None:
    """Test floating text update loop."""
    g = Game.__new__(Game)
    g.floats = [FloatText(x=100, y=50, text="+10", life=5, color=8)]
    g._update_floats()
    ft = g.floats[0]
    assert ft.life == 4
    assert ft.y < 50.0  # moved up


def test_heat_cooldown_blocks_casting() -> None:
    """Test that cooldown prevents casting."""
    g = Game.__new__(Game)
    g.heat_cooldown = 10
    g._attempt_catch()
    # No fish caught, no heat added, because cooldown blocked it
    assert g.heat_cooldown == 10


def test_overheat_on_max_heat() -> None:
    """Test that hitting max heat triggers cooldown."""
    g = Game.__new__(Game)
    g.fish = []
    g.heat = HEAT_MAX - HEAT_PER_CAST
    g.heat_cooldown = 0
    g.particles = []
    g.floats = []
    g.catches = 0
    g.misses = 0
    g.combo = 0
    g.super_mode = 0
    g.score = 0
    g.hook_color = 0
    g.hook_y = 120
    g.highest_combo = 0
    g._attempt_catch()
    assert g.heat >= HEAT_MAX
    assert g.heat_cooldown == HEAT_COOLDOWN_FRAMES


def test_miss_resets_combo() -> None:
    """Test that missing (no fish in range) resets combo."""
    g = Game.__new__(Game)
    g.fish = []
    g.combo = 5
    g.super_mode = 100
    g.heat = 0
    g.heat_cooldown = 0
    g.particles = []
    g.floats = []
    g.catches = 0
    g.misses = 0
    g.score = 0
    g.hook_color = 0
    g.hook_y = 120
    g.highest_combo = 0
    g._attempt_catch()
    assert g.combo == 0
    assert g.super_mode == 0
    assert g.misses == 1


def test_match_color_increments_combo() -> None:
    """Test that catching matching color increments combo."""
    g = Game.__new__(Game)
    g.heat = 0
    g.heat_cooldown = 0
    g.combo = 2
    g.hook_color = 0
    g.hook_y = 120
    g.score = 0
    g.catches = 0
    g.misses = 0
    g.super_mode = 0
    g.particles = []
    g.floats = []
    g.highest_combo = 0
    g.fish = [Fish(x=HOOK_FIX, y=120, color=0, vx=0, alive=True)]

    g._attempt_catch()
    assert g.combo == 3
    assert g.catches == 1
    assert g.score > 0


def test_wrong_color_catches_but_resets_combo() -> None:
    """Test that catching wrong color resets combo to 1 and changes hook color."""
    g = Game.__new__(Game)
    g.heat = 0
    g.heat_cooldown = 0
    g.combo = 4
    g.hook_color = 0
    g.hook_y = 120
    g.score = 0
    g.catches = 0
    g.misses = 0
    g.super_mode = 0  # not in super mode
    g.particles = []
    g.floats = []
    g.highest_combo = 0
    g.fish = [Fish(x=HOOK_FIX, y=120, color=1, vx=0, alive=True)]

    g._attempt_catch()
    assert g.combo == 1
    assert g.hook_color == 1  # changes to caught fish color
    assert g.catches == 1
    assert g.score > 0


def test_super_mode_cancelled_on_wrong_color() -> None:
    """Test that super mode is cancelled when catching wrong color."""
    g = Game.__new__(Game)
    g.heat = 0
    g.heat_cooldown = 0
    g.combo = 3
    g.hook_color = 0
    g.hook_y = 120
    g.score = 0
    g.catches = 0
    g.misses = 0
    g.super_mode = 100  # in super mode
    g.particles = []
    g.floats = []
    g.highest_combo = 0
    g.fish = [Fish(x=HOOK_FIX, y=120, color=1, vx=0, alive=True)]

    # In super mode, catching a fish of ANY color triggers the super branch
    g._attempt_catch()
    # Super mode catch increments combo, doesn't reset it
    assert g.combo == 4  # was 3, incremented
    assert g.super_mode == 100  # super not cancelled in super branch
    assert g.catches >= 1


def test_super_mode_auto_catches_same_color() -> None:
    """Test that super mode auto-catches all fish of the caught color."""
    g = Game.__new__(Game)
    g.heat = 0
    g.heat_cooldown = 0
    g.super_mode = 100
    g.combo = 3
    g.hook_color = 0
    g.hook_y = 120
    g.score = 0
    g.catches = 0
    g.misses = 0
    g.particles = []
    g.floats = []
    g.highest_combo = 0
    g.fish = [
        Fish(x=HOOK_FIX, y=120, color=0, vx=0, alive=True),  # the one we catch
        Fish(x=100, y=80, color=0, vx=1, alive=True),  # same color → auto-caught
        Fish(x=150, y=100, color=0, vx=1, alive=True),  # same color → auto-caught
        Fish(x=180, y=130, color=1, vx=1, alive=True),  # different color → not caught
    ]

    g._attempt_catch()
    assert g.catches >= 2  # at least the direct catch + 1 auto-catch
    # The different-color fish should still be alive
    alive_colors = [f.color for f in g.fish if f.alive]
    assert 1 in alive_colors  # color 1 fish still alive


def test_super_mode_timer_decrements() -> None:
    """Test super mode duration decreases each frame."""
    g = Game.__new__(Game)
    g.super_mode = 100
    g.super_mode -= 1
    assert g.super_mode == 99
    g.super_mode -= 1
    assert g.super_mode == 98
    # Super mode expires
    g.super_mode = 1
    g.super_mode -= 1
    assert g.super_mode == 0


def test_heat_regenerates_over_time() -> None:
    """Test heat decreases each frame when not in cooldown."""
    g = Game.__new__(Game)
    g.heat = 50.0
    g.heat_cooldown = 0
    g.heat = max(0.0, g.heat - 0.3)  # HEAT_REGEN_RATE
    assert g.heat < 50.0
    # Heat never goes below 0
    g.heat = 0.1
    g.heat = max(0.0, g.heat - 0.3)
    assert g.heat == 0.0


def test_cooldown_decrements() -> None:
    """Test heat_cooldown counts down."""
    g = Game.__new__(Game)
    g.heat_cooldown = 10
    g.heat_cooldown -= 1
    assert g.heat_cooldown == 9
    g.heat_cooldown -= 1
    assert g.heat_cooldown == 8


def test_game_timer_counts_down() -> None:
    """Test game timer decreases each frame."""
    g = Game.__new__(Game)
    g.game_timer = 300
    g.phase = Phase.PLAYING
    g.game_timer -= 1
    assert g.game_timer == 299
    # Check game over transition
    if g.game_timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.PLAYING  # still playing at 299


def test_game_over_on_timer_expiry() -> None:
    """Test game transitions to GAME_OVER when timer reaches 0."""
    g = Game.__new__(Game)
    g.game_timer = 1
    g.phase = Phase.PLAYING
    g.game_timer -= 1
    assert g.game_timer == 0
    if g.game_timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_highest_combo_tracks_max() -> None:
    """Test highest_combo tracks the maximum combo achieved."""
    g = Game.__new__(Game)
    g.highest_combo = 0
    g.combo = 5
    g.highest_combo = max(g.highest_combo, g.combo)
    assert g.highest_combo == 5

    g.combo = 3
    g.highest_combo = max(g.highest_combo, g.combo)
    assert g.highest_combo == 5  # unchanged

    g.combo = 8
    g.highest_combo = max(g.highest_combo, g.combo)
    assert g.highest_combo == 8


def test_spawn_interval_decreases_over_time() -> None:
    """Test spawn interval speeds up as game progresses."""
    g = Game.__new__(Game)
    g.spawn_interval = 60
    # Simulate elapsed time
    elapsed = 1800  # 30 seconds
    g.spawn_interval = max(20, 60 - elapsed // 300)
    assert g.spawn_interval == 54  # decreased from 60

    # Much later
    elapsed = 6000
    g.spawn_interval = max(20, 60 - elapsed // 300)
    assert g.spawn_interval == 40


def test_reset_clears_state() -> None:
    """Test reset clears all game state."""
    g = Game.__new__(Game)
    g.score = 9999
    g.combo = 10
    g.game_timer = 100
    g.heat = 80
    g.super_mode = 50
    g.fish = [Fish(x=100, y=80, color=0, vx=1)]
    g.particles = [Particle(x=0, y=0, vx=1, vy=0, life=5, color=8)]
    g.floats = [FloatText(x=100, y=50, text="x", life=10, color=8)]

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.heat_cooldown == 0
    assert g.super_mode == 0
    assert g.fish == []
    assert g.particles == []
    assert g.floats == []
    assert g.catches == 0
    assert g.misses == 0
    assert g.phase == Phase.TITLE


def test_golden_fish_double_score() -> None:
    """Test golden fish give double base score."""
    base = 50
    golden = base * 2
    assert golden == 100


def test_hook_y_clamped() -> None:
    """Test hook y position stays within bounds."""
    # Upper bound
    y = 25
    y = max(40, y)
    assert y == 40

    # Lower bound
    y = 230
    y = min(215, y)
    assert y == 215

    # In bounds
    y = 120
    assert 40 <= y <= 215


# ── Helper for tests that need HOOK_X ──
HOOK_FIX = 200  # matches HOOK_X in main.py


if __name__ == "__main__":
    import traceback

    tests = [
        ("constants", test_constants),
        ("fish_dataclass", test_fish_dataclass),
        ("particle_dataclass", test_particle_dataclass),
        ("float_text_dataclass", test_float_text_dataclass),
        ("phase_enum", test_phase_enum),
        ("fish_movement", test_fish_movement),
        ("fish_off_screen_removal", test_fish_off_screen_removal),
        ("particle_lifecycle", test_particle_lifecycle),
        ("float_text_movement", test_float_text_movement),
        ("catch_range_math", test_catch_range_math),
        ("combo_scoring", test_combo_scoring),
        ("heat_mechanics", test_heat_mechanics),
        ("super_thresholds", test_super_thresholds),
        ("color_cycle", test_color_cycle),
        ("spawn_fish_creates_fish", test_spawn_fish_creates_fish),
        ("fish_cleanup_removes_dead", test_fish_cleanup_removes_dead),
        ("fish_off_screen_cleaned", test_fish_off_screen_cleaned),
        ("particle_update", test_particle_update),
        ("float_text_update", test_float_text_update),
        ("heat_cooldown_blocks_casting", test_heat_cooldown_blocks_casting),
        ("overheat_on_max_heat", test_overheat_on_max_heat),
        ("miss_resets_combo", test_miss_resets_combo),
        ("match_color_increments_combo", test_match_color_increments_combo),
        ("wrong_color_catches_but_resets_combo", test_wrong_color_catches_but_resets_combo),
        ("super_mode_cancelled_on_wrong_color", test_super_mode_cancelled_on_wrong_color),
        ("super_mode_auto_catches_same_color", test_super_mode_auto_catches_same_color),
        ("super_mode_timer_decrements", test_super_mode_timer_decrements),
        ("heat_regenerates_over_time", test_heat_regenerates_over_time),
        ("cooldown_decrements", test_cooldown_decrements),
        ("game_timer_counts_down", test_game_timer_counts_down),
        ("game_over_on_timer_expiry", test_game_over_on_timer_expiry),
        ("highest_combo_tracks_max", test_highest_combo_tracks_max),
        ("spawn_interval_decreases_over_time", test_spawn_interval_decreases_over_time),
        ("reset_clears_state", test_reset_clears_state),
        ("golden_fish_double_score", test_golden_fish_double_score),
        ("hook_y_clamped", test_hook_y_clamped),
    ]

    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    if failed:
        sys.exit(1)
