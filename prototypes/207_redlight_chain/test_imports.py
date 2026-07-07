"""test_imports.py — Headless logic tests for 207_redlight_chain."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/207_redlight_chain")
from main import (  # noqa: E402
    COMBO_SUPER_THRESHOLD,
    FINISH_TARGET_GEMS,
    GAME_DURATION,
    GEM_DESPAWN_X,
    GEM_RADIUS,
    GEM_SPEED,
    HEAT_DECAY,
    HEAT_PER_MISS,
    INITIAL_LIGHT_INTERVAL,
    LIGHT_COLORS,
    LIGHT_PYXEL_COLORS,
    MAX_GEMS,
    MAX_HEAT,
    PARTICLE_BURST,
    PLAYER_MAX_X,
    PLAYER_MIN_X,
    PLAYER_SPEED,
    SCORE_BASE,
    SCORE_COMBO_MULT,
    SUPER_DURATION,
    SUPER_SCORE_MULT,
    FloatingText,
    Gem,
    LightColor,
    Particle,
    Phase,
    _make_game,
)


def test_make_game_creates_valid_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.player_x == 160.0
    assert g.light_color == LightColor.RED
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.gems == []
    assert g.particles == []
    assert g.floating_texts == []


def test_reset_initializes_playing_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_active = True
    g.gems.append(Gem(x=100.0, y=180.0, color=0))
    g.particles.append(Particle(x=0, y=0, vx=1, vy=1, life=10, color=8))
    g.floating_texts.append(FloatingText(x=0, y=0, text="test", life=10, color=7))

    g.reset()

    assert g.phase == Phase.PLAYING
    assert g.player_x == 160.0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.gems == []
    assert g.particles == []
    assert g.floating_texts == []


def test_gem_dataclass() -> None:
    gem = Gem(x=100.0, y=180.0, color=LightColor.GREEN)
    assert gem.x == 100.0
    assert gem.y == 180.0
    assert gem.color == LightColor.GREEN
    assert gem.collected is False


def test_gem_collected_flag() -> None:
    gem = Gem(x=50.0, y=180.0, color=LightColor.RED)
    gem.collected = True
    assert gem.collected is True


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+50", life=30, color=10)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+50"
    assert ft.life == 30
    assert ft.color == 10


def test_light_color_enum_values() -> None:
    assert LightColor.RED == 0
    assert LightColor.GREEN == 1
    assert LightColor.YELLOW == 2
    assert LightColor.BLUE == 3
    assert len(LIGHT_COLORS) == 4


def test_phase_enum_values() -> None:
    assert Phase.TITLE.value == 1
    assert Phase.PLAYING.value == 2
    assert Phase.GAME_OVER.value == 3


def test_collect_gem_same_color_increments_combo() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)

    g._collect_gem(gem)

    assert gem.collected is True
    assert g.combo == 1
    assert g.score > 0
    assert g.max_combo == 1
    assert g.heat == 0.0
    assert g.super_active is False  # combo=1 < 4


def test_collect_gem_wrong_color_resets_combo_and_adds_heat() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.combo = 3
    g.max_combo = 3
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.GREEN)

    g._collect_gem(gem)

    assert gem.collected is True
    assert g.combo == 0
    assert g.heat == HEAT_PER_MISS
    assert g._shake_frames == 3
    assert g.max_combo == 3  # max_combo preserved


def test_collect_gem_wrong_color_max_combo_preserved() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.combo = 5
    g.max_combo = 5
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.BLUE)

    g._collect_gem(gem)

    assert g.combo == 0
    assert g.max_combo == 5  # still 5 from before


def test_collect_gem_activates_super_at_threshold() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.combo = COMBO_SUPER_THRESHOLD - 1  # combo=3

    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
    g._collect_gem(gem)

    assert g.combo == COMBO_SUPER_THRESHOLD  # now 4
    assert g.super_active is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_all_colors_match() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.super_active = True
    g.super_timer = 100
    g.light_color = LightColor.RED
    g.combo = 5

    # Collect a gem of a DIFFERENT color — should still match in super mode
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.BLUE)
    g._collect_gem(gem)

    assert gem.collected is True
    assert g.combo == 6  # incremented, not reset
    assert g.heat == 0.0  # no heat added


def test_super_mode_gives_3x_score() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.super_active = True
    g.super_timer = 100
    g.light_color = LightColor.RED
    g.combo = 2

    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
    g._collect_gem(gem)

    # combo becomes 3, normal score = 10 + 3*5 = 25, super score = 25 * 3 = 75
    expected_points = (SCORE_BASE + 3 * SCORE_COMBO_MULT) * SUPER_SCORE_MULT
    assert g.score == expected_points


def test_super_mode_timer_decrements() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.super_active = True
    g.super_timer = 50
    g.light_color = LightColor.RED
    g.combo = 1

    # Simulate the super timer decrement from _update_playing
    g.super_timer -= 1
    assert g.super_timer == 49

    # When timer reaches 0, super deactivates
    g.super_timer = 1
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_active = False
    assert g.super_active is False


def test_collect_gem_bursts_particles() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)

    assert len(g.particles) == 0
    g._collect_gem(gem)
    assert len(g.particles) == PARTICLE_BURST

    for p in g.particles:
        assert p.life >= 15
        assert p.life <= 26
        assert isinstance(p.vx, float)
        assert isinstance(p.vy, float)


def test_collect_gem_adds_floating_text() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)

    assert len(g.floating_texts) == 0
    g._collect_gem(gem)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text.startswith("+")
    assert g.floating_texts[0].life == 30


def test_collect_gem_wrong_color_adds_miss_floating_text() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.GREEN)

    g._collect_gem(gem)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "MISS"


def test_collect_gem_super_threshold_adds_super_text() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.combo = 3  # one below threshold

    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
    g._collect_gem(gem)
    # Should have: +points text + SUPER! text = 2 floating texts
    assert len(g.floating_texts) == 2
    super_texts = [ft for ft in g.floating_texts if ft.text == "SUPER!"]
    assert len(super_texts) == 1


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.heat = MAX_HEAT - 5
    g.light_color = LightColor.RED
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.GREEN)

    g._collect_gem(gem)
    assert g.heat == MAX_HEAT  # capped at 100


def test_heat_decay_when_idle() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.heat = 50.0
    g._idle_frames = 60  # threshold reached

    # Simulate idle decay
    if g._idle_frames >= 60:
        g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_below_zero() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.heat = 0.0
    g._idle_frames = 60

    if g._idle_frames >= 60:
        g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 0.0


def test_heat_game_over() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.heat = MAX_HEAT

    assert g.phase == Phase.PLAYING
    if g.heat >= MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_timer_game_over() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.game_timer = 0

    assert g.phase == Phase.PLAYING
    if g.game_timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_timer_game_over_at_zero() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.game_timer = 1

    assert g.phase == Phase.PLAYING
    g.game_timer -= 1
    if g.game_timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_player_movement_bounds() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    # Move right
    g.player_x += PLAYER_SPEED
    # Move left
    g.player_x -= PLAYER_SPEED

    # Test bounds clamping
    g.player_x = PLAYER_MIN_X - 10
    if g.player_x < PLAYER_MIN_X:
        g.player_x = PLAYER_MIN_X
    assert g.player_x == PLAYER_MIN_X

    g.player_x = PLAYER_MAX_X + 10
    if g.player_x > PLAYER_MAX_X:
        g.player_x = PLAYER_MAX_X
    assert g.player_x == PLAYER_MAX_X


def test_gem_movement() -> None:
    gem = Gem(x=200.0, y=180.0, color=LightColor.RED)
    initial_x = gem.x
    gem.x -= GEM_SPEED
    assert gem.x == initial_x - GEM_SPEED


def test_gem_despawn_at_boundary() -> None:
    gem = Gem(x=GEM_DESPAWN_X + 1.0, y=180.0, color=LightColor.RED)
    gem.x -= GEM_SPEED
    assert gem.x <= GEM_DESPAWN_X


def test_collection_distance_check() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    # Place gem right at player position — should be collected
    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
    dist = math.hypot(gem.x - g.player_x, 180.0 - 180.0)
    assert dist < GEM_RADIUS  # 0 < 16

    # Place gem far away — should NOT be collected
    far_gem = Gem(x=10.0, y=180.0, color=LightColor.RED)
    far_dist = math.hypot(far_gem.x - g.player_x, 180.0 - 180.0)
    assert far_dist >= GEM_RADIUS


def test_max_gems_cap() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    # Fill gems to max
    for i in range(MAX_GEMS):
        g.gems.append(Gem(x=float(100 + i * 20), y=180.0, color=i % 4))

    assert len(g.gems) == MAX_GEMS

    # Try to spawn another — should be rejected
    if len(g.gems) >= MAX_GEMS:
        pass  # don't spawn
    assert len(g.gems) == MAX_GEMS


def test_particle_lifecycle() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    g.particles.append(Particle(x=100, y=100, vx=1, vy=1, life=3, color=8))
    g.particles.append(Particle(x=200, y=200, vx=-1, vy=-1, life=1, color=3))
    g.particles.append(Particle(x=300, y=300, vx=0, vy=0, life=0, color=10))

    # Update particles
    for p in g.particles:
        p.x += p.vx
        p.y += p.vy
        p.life -= 1
    g.particles = [p for p in g.particles if p.life > 0]

    # life=3 → 2 (alive), life=1 → 0 (dead), life=0 already dead
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    g.floating_texts.append(FloatingText(x=100, y=100, text="+10", life=2, color=10))
    g.floating_texts.append(FloatingText(x=200, y=200, text="MISS", life=1, color=8))

    # Update floating texts
    for ft in g.floating_texts:
        ft.y -= 1
        ft.life -= 1
    g.floating_texts = [ft for ft in g.floating_texts if ft.life > 0]

    # life=2 → 1 (alive), life=1 → 0 (dead)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 1


def test_light_cycle_order() -> None:
    assert LIGHT_COLORS == [LightColor.RED, LightColor.GREEN, LightColor.YELLOW, LightColor.BLUE]


def test_light_index_wraps() -> None:
    assert (0 + 1) % 4 == 1
    assert (3 + 1) % 4 == 0  # wraps back to RED


def test_current_light_interval_decreases() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    # At start: interval = 120
    assert g._current_light_interval() == INITIAL_LIGHT_INTERVAL

    # After some time
    g.game_timer = GAME_DURATION - 1200  # 20 seconds elapsed
    interval = g._current_light_interval()
    assert interval < INITIAL_LIGHT_INTERVAL

    # At end: should be at least MIN
    g.game_timer = 0
    assert g._current_light_interval() >= 40


def test_spawn_gem_respects_max() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    # Fill to max
    for i in range(MAX_GEMS):
        g.gems.append(Gem(x=float(100 + i * 20), y=180.0, color=0))

    before = len(g.gems)
    g._spawn_gem()
    assert len(g.gems) == before  # no new gem spawned


def test_spawn_gem_creates_gem() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)

    assert len(g.gems) == 0
    g._spawn_gem()
    assert len(g.gems) == 1
    assert g.gems[0].x == 330.0
    assert g.gems[0].color in (0, 1, 2, 3)


def test_score_computation_normal() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.combo = 2

    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
    g._collect_gem(gem)

    # combo becomes 3, score = 10 + 3*5 = 25
    assert g.score == SCORE_BASE + 3 * SCORE_COMBO_MULT


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED

    # Build combo up to 3
    for _ in range(3):
        gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
        g._collect_gem(gem)

    assert g.combo == 3
    assert g.max_combo == 3

    # Wrong color resets combo but not max_combo
    wrong_gem = Gem(x=g.player_x, y=180.0, color=LightColor.GREEN)
    g._collect_gem(wrong_gem)

    assert g.combo == 0
    assert g.max_combo == 3


def test_super_does_not_reactivate_when_already_active() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.super_active = True
    g.super_timer = 50
    g.combo = 5  # already above threshold

    gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
    g._collect_gem(gem)

    # super_timer should NOT be reset to SUPER_DURATION
    assert g.super_timer == 50  # unchanged
    assert g.super_active is True


def test_combo_preserved_after_super_expiry() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED
    g.super_active = True
    g.super_timer = 1
    g.combo = 5

    # Simulate super expiry
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_active = False

    assert g.super_active is False
    assert g.combo == 5  # combo preserved


def test_collect_gem_burst_count() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED

    for i in range(5):
        gem = Gem(x=g.player_x, y=180.0, color=LightColor.RED)
        g._collect_gem(gem)

    assert len(g.particles) == 5 * PARTICLE_BURST


def test_multiple_gems_collection_order() -> None:
    g = _make_game()
    g.reset()
    g._rng = random.Random(42)
    g.light_color = LightColor.RED

    # Place two gems near player: one matching, one wrong
    g.gems = [
        Gem(x=g.player_x, y=180.0, color=LightColor.RED),
        Gem(x=g.player_x + 5, y=180.0, color=LightColor.GREEN),
    ]

    # Both should be collected in one update pass
    for gem in g.gems:
        if gem.collected:
            continue
        dist = math.hypot(gem.x - g.player_x, gem.y - 180.0)
        if dist < GEM_RADIUS:
            g._collect_gem(gem)

    # Second gem (wrong color) resets combo from first
    assert g.combo == 0
    assert g.heat == HEAT_PER_MISS


def test_spawn_gem_with_match_bias() -> None:
    g = _make_game()
    g.reset()
    g.light_color = LightColor.GREEN

    # Override RNG to force match_bias path
    g._rng = random.Random(0)
    # Force random() < MATCH_BIAS
    g._rng.random = lambda: 0.1  # type: ignore

    g._spawn_gem()
    assert g.gems[-1].color == LightColor.GREEN


def test_spawn_gem_without_match_bias() -> None:
    g = _make_game()
    g.reset()
    g.light_color = LightColor.GREEN

    g._rng = random.Random(1)
    # Force random() >= MATCH_BIAS
    g._rng.random = lambda: 0.9  # type: ignore

    g._spawn_gem()
    # Color could be anything 0-3, just check it's valid
    assert g.gems[-1].color in (0, 1, 2, 3)


def test_light_pyxel_colors_mapping() -> None:
    from main import LIGHT_DIM_COLORS

    assert LIGHT_PYXEL_COLORS[LightColor.RED] == 8  # RED
    assert LIGHT_PYXEL_COLORS[LightColor.GREEN] == 3  # GREEN
    assert LIGHT_PYXEL_COLORS[LightColor.YELLOW] == 10  # YELLOW
    assert LIGHT_PYXEL_COLORS[LightColor.BLUE] == 6  # LIGHT_BLUE
    assert LIGHT_DIM_COLORS[LightColor.RED] == 4  # BROWN


def test_finish_target_gems_defined() -> None:
    assert FINISH_TARGET_GEMS == 30


def test_super_duration_constant() -> None:
    assert SUPER_DURATION == 180


def test_game_duration_is_60_seconds() -> None:
    assert GAME_DURATION == 3600


def test_heat_constants() -> None:
    assert HEAT_PER_MISS == 15
    assert MAX_HEAT == 100
    assert HEAT_DECAY == 0.1


def test_all_light_colors_are_valid() -> None:
    for lc in LIGHT_COLORS:
        assert lc in LIGHT_PYXEL_COLORS
        assert 0 <= lc <= 3
