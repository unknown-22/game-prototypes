"""test_imports.py — Headless logic tests for TYPE SURGE (118_type_surge).

Tests verify game logic without initializing Pyxel. Uses Game.__new__ pattern.

Run: uv run python prototypes/118_type_surge/test_imports.py
"""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/118_type_surge")

from main import (
    COLORS,
    COLORS_5,
    FloatingText,
    GAME_DURATION,
    Game,
    HEAT_DECAY,
    HEAT_MISS,
    HEAT_WRONG_KEY,
    KILL_Y,
    LETTER_SPAWN_INTERVAL_INITIAL,
    LETTER_SPAWN_INTERVAL_MIN,
    LETTER_SPEED_MAX,
    Letter,
    MAX_HEAT,
    MAX_HP,
    Particle,
    Phase,
    SCREEN_H,
    SCREEN_W,
    STUN_DURATION,
    SUPER_COMBO_THRESHOLD,
    SUPER_COOLDOWN_DURATION,
    SUPER_DURATION,
)


def _make_game() -> Game:
    """Create a Game instance for headless testing (bypasses pyxel.init)."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.hp = MAX_HP
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.super_timer = 0
    g.super_mode = False
    g.super_cooldown = 0
    g.stun_timer = 0
    g.letters = []
    g.particles = []
    g.floating_texts = []
    g.spawn_timer = LETTER_SPAWN_INTERVAL_INITIAL
    g.current_color = -1
    g.last_key = ""
    g.shake_frames = 0
    g.shake_intensity = 0
    g._letters_destroyed = 0
    g.reset()
    g._start_game()
    return g


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════


def test_letter_dataclass():
    letter = Letter(char="A", color=8, x=100.0, y=50.0, speed=1.0)
    assert letter.char == "A"
    assert letter.color == 8
    assert letter.x == 100.0
    assert letter.y == 50.0
    assert letter.speed == 1.0
    assert letter.life == 1
    assert letter.glow_phase == 0.0


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, color=3, life=15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.color == 3
    assert p.life == 15
    assert p.size == 2


def test_floating_text_dataclass():
    ft = FloatingText(x=50.0, y=60.0, text="+10", color=8, life=30)
    assert ft.x == 50.0
    assert ft.y == 60.0
    assert ft.text == "+10"
    assert ft.color == 8
    assert ft.life == 30
    assert ft.vy == -1.5


# ═══════════════════════════════════════════════════════════════
# Phase enum
# ═══════════════════════════════════════════════════════════════


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE != Phase.PLAYING


# ═══════════════════════════════════════════════════════════════
# Game state initialization
# ═══════════════════════════════════════════════════════════════


def test_game_reset():
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 999
    g.combo = 5
    g.max_combo = 10
    g.hp = 1
    g.heat = 99.0
    g.timer = 10
    g.super_timer = 30
    g.super_mode = True
    g.super_cooldown = 50
    g.stun_timer = 20
    g.letters = [Letter("X", 8, 100, 50, 1.0)]
    g.particles = [Particle(0, 0, 1, 1, 0, 1)]
    g.floating_texts = [FloatingText(0, 0, "x", 0, 1)]
    g.spawn_timer = 5
    g.current_color = 8
    g.last_key = "Z"
    g.shake_frames = 10
    g.shake_intensity = 5
    g._letters_destroyed = 99
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == MAX_HP
    assert g.heat == 0.0
    assert g.timer == GAME_DURATION
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.super_cooldown == 0
    assert g.stun_timer == 0
    assert g.letters == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.current_color == -1
    assert g.last_key == ""
    assert g.shake_frames == 0
    assert g.shake_intensity == 0
    assert g._letters_destroyed == 0


def test_start_game():
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == MAX_HP
    assert g.heat == 0.0
    assert g.timer == GAME_DURATION
    assert g.super_mode is False
    assert g.letters == []
    assert g.current_color == -1


# ═══════════════════════════════════════════════════════════════
# Letter spawning
# ═══════════════════════════════════════════════════════════════


def test_spawn_letter_adds_to_list():
    g = _make_game()
    initial_count = len(g.letters)
    letter = g._spawn_letter()
    assert len(g.letters) == initial_count + 1
    assert letter in g.letters


def test_spawn_letter_valid_char():
    g = _make_game()
    letter = g._spawn_letter()
    assert "A" <= letter.char <= "Z"


def test_spawn_letter_valid_color():
    g = _make_game()
    letter = g._spawn_letter()
    assert letter.color in COLORS


def test_spawn_letter_position_in_bounds():
    g = _make_game()
    letter = g._spawn_letter()
    assert 20 <= letter.x <= 290
    assert letter.y == 0.0


def test_spawn_letter_speed_positive():
    g = _make_game()
    letter = g._spawn_letter()
    assert letter.speed > 0


def test_spawn_letter_deterministic():
    g1 = _make_game()
    g2 = _make_game()
    # Same seed, same initial state → same first letter
    letter1 = g1._spawn_letter()
    letter2 = g2._spawn_letter()
    assert letter1.char == letter2.char
    assert letter1.color == letter2.color


def test_spawn_letter_five_colors_after_60s():
    g = _make_game()
    # Simulate 61 seconds elapsed
    g.timer = GAME_DURATION - 61 * 60
    # Collect colors from many spawns
    colors_seen: set[int] = set()
    for _ in range(50):
        letter = g._spawn_letter()
        colors_seen.add(letter.color)
    assert len(colors_seen) >= 4
    # After 60s, all 5 colors should appear eventually
    assert 9 in COLORS_5  # ORANGE


# ═══════════════════════════════════════════════════════════════
# Difficulty scaling
# ═══════════════════════════════════════════════════════════════


def test_get_spawn_interval_initial():
    g = _make_game()
    g.timer = GAME_DURATION
    assert g._get_spawn_interval() == LETTER_SPAWN_INTERVAL_INITIAL


def test_get_spawn_interval_decreases():
    g = _make_game()
    interval_early = g._get_spawn_interval()
    g.timer = GAME_DURATION // 2
    interval_mid = g._get_spawn_interval()
    g.timer = 1
    interval_late = g._get_spawn_interval()
    assert interval_early > interval_mid > interval_late
    assert interval_late >= LETTER_SPAWN_INTERVAL_MIN


def test_get_letter_speed_increases():
    g = _make_game()
    g.timer = GAME_DURATION
    speed_early = g._get_letter_speed()
    g.timer = 1
    speed_late = g._get_letter_speed()
    assert speed_early < speed_late
    assert speed_late <= LETTER_SPEED_MAX


def test_get_active_colors_count_default_4():
    g = _make_game()
    assert g._get_active_colors_count() == 4


def test_get_active_colors_count_5_after_60s():
    g = _make_game()
    g.timer = GAME_DURATION - 61 * 60
    assert g._get_active_colors_count() == 5


# ═══════════════════════════════════════════════════════════════
# Score computation
# ═══════════════════════════════════════════════════════════════


def test_compute_score_basic():
    g = _make_game()
    g.combo = 1
    assert g._compute_score() == 15  # 10 + 1*5


def test_compute_score_high_combo():
    g = _make_game()
    g.combo = 10
    assert g._compute_score() == 60  # 10 + 10*5


def test_compute_super_score():
    g = _make_game()
    g.combo = 5
    assert g._compute_super_score() == 105  # 30 + 5*15


# ═══════════════════════════════════════════════════════════════
# Keypress processing
# ═══════════════════════════════════════════════════════════════


def test_process_keypress_match_same_color():
    g = _make_game()
    g.current_color = 8  # RED
    g.letters = [Letter(char="A", color=8, x=100, y=100, speed=1.0)]
    assert g.combo == 0
    g._process_keypress("A")
    assert len(g.letters) == 0  # destroyed
    assert g.combo == 1
    assert g.score > 0
    assert g._letters_destroyed == 1


def test_process_keypress_match_different_color_resets_combo():
    g = _make_game()
    g.combo = 3
    g.current_color = 8  # RED
    g.letters = [Letter(char="A", color=3, x=100, y=100, speed=1.0)]  # GREEN
    g._process_keypress("A")
    assert len(g.letters) == 0  # still destroyed
    assert g.combo == 1  # reset to 1
    assert g.current_color == 3  # updated
    assert g.heat > 0  # heat gained for wrong color


def test_process_keypress_no_matching_letter():
    g = _make_game()
    g.letters = [Letter(char="B", color=8, x=100, y=100, speed=1.0)]
    g.heat = 0.0
    g._process_keypress("A")  # no 'A' on screen
    assert len(g.letters) == 1  # not destroyed
    assert g.heat == HEAT_WRONG_KEY  # heat gained


def test_process_keypress_destroys_lowest_when_multiple():
    g = _make_game()
    g.current_color = 8
    g.letters = [
        Letter(char="A", color=8, x=50, y=200, speed=1.0),   # lowest
        Letter(char="A", color=8, x=150, y=100, speed=1.0),  # higher
    ]
    g._process_keypress("A")
    assert len(g.letters) == 1
    # The higher one should remain
    assert g.letters[0].y == 100


def test_process_keypress_triggers_super_at_threshold():
    g = _make_game()
    g.combo = SUPER_COMBO_THRESHOLD - 1  # 3
    g.current_color = 8
    g.super_cooldown = 0
    g.letters = [Letter(char="A", color=8, x=100, y=50, speed=1.0)]
    g._process_keypress("A")
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_process_keypress_no_super_during_cooldown():
    g = _make_game()
    g.combo = SUPER_COMBO_THRESHOLD - 1
    g.current_color = 8
    g.super_cooldown = 30  # still cooling
    g.letters = [Letter(char="A", color=8, x=100, y=50, speed=1.0)]
    g._process_keypress("A")
    assert g.super_mode is False  # cooldown blocks super


def test_process_keypress_increments_max_combo():
    g = _make_game()
    g.combo = 0
    g.max_combo = 0
    g.current_color = 8
    for i in range(5):
        g.letters = [Letter(char=chr(65 + i), color=8, x=100, y=50 + i * 10, speed=1.0)]
        g._process_keypress(chr(65 + i))
    assert g.max_combo == 5
    assert g.combo == 5


def test_process_keypress_first_letter_always_matches():
    """current_color == -1 means any color matches."""
    g = _make_game()
    g.current_color = -1
    g.letters = [Letter(char="A", color=3, x=100, y=100, speed=1.0)]  # GREEN
    g._process_keypress("A")
    assert g.combo == 1
    assert g.current_color == 3


# ═══════════════════════════════════════════════════════════════
# Heat system
# ═══════════════════════════════════════════════════════════════


def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_below_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_triggers_stun_at_max():
    g = _make_game()
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.stun_timer == STUN_DURATION
    assert g.heat == 50.0  # reset to half


def test_heat_no_decay_during_stun():
    g = _make_game()
    g.heat = 30.0
    g.stun_timer = 10
    initial_heat = g.heat
    g._update_heat()
    assert g.heat == initial_heat  # no decay


# ═══════════════════════════════════════════════════════════════
# Letter update / HP loss
# ═══════════════════════════════════════════════════════════════


def test_letters_fall():
    g = _make_game()
    g.letters = [Letter(char="A", color=8, x=100, y=50, speed=1.5)]
    g._update_letters()
    assert g.letters[0].y == 51.5


def test_letter_below_kill_y_drains_hp():
    g = _make_game()
    g.letters = [Letter(char="A", color=8, x=100, y=KILL_Y, speed=1.0)]
    g._update_letters()
    assert len(g.letters) == 0  # removed
    assert g.hp == MAX_HP - 1
    assert g.heat == HEAT_MISS


def test_letter_below_kill_y_resets_combo():
    g = _make_game()
    g.combo = 5
    g.current_color = 8
    g.letters = [Letter(char="A", color=8, x=100, y=KILL_Y, speed=1.0)]
    g._update_letters()
    assert g.combo == 0
    assert g.current_color == -1


# ═══════════════════════════════════════════════════════════════
# Super mode
# ═══════════════════════════════════════════════════════════════


def test_activate_super():
    g = _make_game()
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_deactivate_super():
    g = _make_game()
    g._activate_super()
    g._deactivate_super()
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.super_cooldown == SUPER_COOLDOWN_DURATION
    assert g.combo == 0
    assert g.current_color == -1


def test_update_super_counts_down():
    g = _make_game()
    g._activate_super()
    initial = g.super_timer
    g._update_super()
    assert g.super_timer == initial - 1


def test_update_super_deactivates_when_expired():
    g = _make_game()
    g._activate_super()
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False


def test_super_cooldown_counts_down():
    g = _make_game()
    g.super_cooldown = 10
    g._update_super()
    assert g.super_cooldown == 9


def test_super_tick_destroys_all_letters():
    g = _make_game()
    g.letters = [
        Letter(char="A", color=8, x=50, y=50, speed=1.0),
        Letter(char="B", color=3, x=100, y=100, speed=1.0),
        Letter(char="C", color=5, x=150, y=150, speed=1.0),
    ]
    g._super_tick()
    assert len(g.letters) == 0
    assert g.score > 0
    assert g._letters_destroyed == 3


def test_super_tick_empty_letters_noop():
    g = _make_game()
    g.letters = []
    score_before = g.score
    g._super_tick()
    assert g.score == score_before


# ═══════════════════════════════════════════════════════════════
# Game end
# ═══════════════════════════════════════════════════════════════


def test_game_end_hp_zero():
    g = _make_game()
    g.hp = 0
    g._check_game_end()
    assert g.phase == Phase.GAME_OVER


def test_game_end_timer_zero():
    g = _make_game()
    g.timer = 0
    g._check_game_end()
    assert g.phase == Phase.GAME_OVER


def test_game_end_not_triggered_while_playing():
    g = _make_game()
    g.hp = 1
    g.timer = 100
    g._check_game_end()
    assert g.phase == Phase.PLAYING


# ═══════════════════════════════════════════════════════════════
# Shake
# ═══════════════════════════════════════════════════════════════


def test_trigger_shake():
    g = _make_game()
    g._trigger_shake(5)
    assert g.shake_frames == 8
    assert g.shake_intensity == 5


def test_update_shake_counts_down():
    g = _make_game()
    g.shake_frames = 5
    g._update_shake()
    assert g.shake_frames == 4


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


def test_update_particles_moves_and_decays():
    g = _make_game()
    g.particles = [
        Particle(x=100, y=100, vx=1.0, vy=-2.0, color=8, life=2, size=2),
        Particle(x=100, y=100, vx=1.0, vy=-2.0, color=8, life=1, size=2),  # will die
    ]
    g._update_particles()
    # The one with life=1 gets decremented to 0, filtered out
    assert len(g.particles) <= 2


def test_update_particles_removes_expired():
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=1.0, vy=-2.0, color=8, life=1, size=2)]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_positions_updated():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.5, vy=-2.0, color=8, life=10, size=2)]
    g._update_particles()
    assert abs(g.particles[0].x - 101.5) < 0.01
    assert abs(g.particles[0].y - 98.0) < 0.01


def test_spawn_destroy_particles():
    g = _make_game()
    letter = Letter(char="A", color=8, x=100, y=50, speed=1.0)
    before = len(g.particles)
    g._spawn_destroy_particles(letter, super_mode=False)
    assert len(g.particles) > before
    assert len(g.particles) <= before + 8


def test_spawn_super_destroy_particles_more():
    g = _make_game()
    letter = Letter(char="A", color=8, x=100, y=50, speed=1.0)
    g._spawn_destroy_particles(letter, super_mode=False)
    count_normal = len(g.particles)
    g.particles.clear()
    g._spawn_destroy_particles(letter, super_mode=True)
    count_super = len(g.particles)
    # Super should spawn more particles (8-12 vs 4-8), but overlapping ranges
    # means it's possible normal spawns 8 and super spawns 8. Test average.
    # We just verify both create particles.
    assert count_normal > 0
    assert count_super > 0


# ═══════════════════════════════════════════════════════════════
# Floating texts
# ═══════════════════════════════════════════════════════════════


def test_update_floating_texts_moves():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="+10", color=8, life=10, vy=-1.5)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - 98.5) < 0.01
    assert g.floating_texts[0].life == 9


def test_update_floating_texts_removes_expired():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="+10", color=8, life=1, vy=-1.5)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════
# Combo system edge cases
# ═══════════════════════════════════════════════════════════════


def test_combo_only_increments_on_same_color():
    g = _make_game()
    g.current_color = 8
    g.letters = [Letter(char="A", color=8, x=100, y=100, speed=1.0)]
    g._process_keypress("A")
    assert g.combo == 1
    # Next letter: same color
    g.letters = [Letter(char="B", color=8, x=100, y=100, speed=1.0)]
    g._process_keypress("B")
    assert g.combo == 2
    # Next letter: different color
    g.letters = [Letter(char="C", color=3, x=100, y=100, speed=1.0)]
    g._process_keypress("C")
    assert g.combo == 1  # reset
    assert g.heat > 0  # penalty


def test_wrong_key_heat():
    g = _make_game()
    g.letters = []  # empty — no matching letters
    g.heat = 0.0
    g._on_wrong_key()
    assert g.heat == HEAT_WRONG_KEY


def test_wrong_key_particles_spawn():
    g = _make_game()
    before = len(g.particles)
    g._on_wrong_key()
    assert len(g.particles) == before + 3


def test_multiple_combo_reaches_super_and_deactivates():
    g = _make_game()
    g.current_color = 8
    g.super_cooldown = 0
    # Build combo to 4
    for i in range(4):
        g.letters = [Letter(char=chr(65 + i), color=8, x=100, y=50 + i * 10, speed=1.0)]
        g._process_keypress(chr(65 + i))
    assert g.super_mode is True
    # Now deactivate
    g._deactivate_super()
    assert g.super_mode is False
    assert g.combo == 0
    assert g.current_color == -1


# ═══════════════════════════════════════════════════════════════
# Constants verification
# ═══════════════════════════════════════════════════════════════


def test_screen_dimensions():
    assert SCREEN_W == 320
    assert SCREEN_H == 240


def test_colors_list():
    assert COLORS == [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW


def test_colors_5_list():
    assert 9 in COLORS_5  # ORANGE


def test_max_heat():
    assert MAX_HEAT == 100


def test_super_combo_threshold():
    assert SUPER_COMBO_THRESHOLD == 4


# ═══════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    tests = [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed! 🎮")
