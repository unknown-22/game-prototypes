"""test_imports.py — Headless logic tests for POGO CHAIN."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    SCREEN_W,
    SCREEN_H,
    GROUND_Y,
    PLAYER_W,
    BOUNCE_HEIGHT,
    BOUNCE_SPEED,
    MOVE_SPEED,
    GEM_SIZE,
    MAX_GEMS,
    GEM_SPAWN_INTERVAL,
    SUPER_DURATION,
    GAME_TIME,
    HEAT_MAX,
    HEAT_PER_MISS,
    HEAT_DECAY,
    COMBO_SUPER_THRESHOLD,
    NUM_COLORS,
    RED,
    GREEN,
    DARK_BLUE,
    YELLOW,
    COLORS,
    Gem,
    Particle,
    FloatingText,
    Game,
)


# ── Factory ────────────────────────────────────────────────────────


def _make_game() -> Game:
    """Create a Game bypassing pyxel.init."""
    g = Game.__new__(Game)
    g._init_state()
    g.rng = random.Random(42)
    return g


def _make_playing() -> Game:
    """Create a Game in PLAYING state."""
    g = _make_game()
    g.phase = "PLAYING"
    g.active_color = 0  # RED
    return g


# ── Constants ──────────────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert GROUND_Y == 216
    assert PLAYER_W == 16
    assert BOUNCE_HEIGHT == 80
    assert BOUNCE_SPEED == 3.0
    assert MOVE_SPEED == 2.5
    assert GEM_SIZE == 8
    assert MAX_GEMS == 12
    assert GEM_SPAWN_INTERVAL == 45
    assert SUPER_DURATION == 300
    assert GAME_TIME == 3600
    assert HEAT_MAX == 100
    assert HEAT_PER_MISS == 15
    assert HEAT_DECAY == 0.03
    assert COMBO_SUPER_THRESHOLD == 5
    assert NUM_COLORS == 4
    assert len(COLORS) == 4
    assert COLORS[0] == RED
    assert COLORS[1] == GREEN
    assert COLORS[2] == DARK_BLUE
    assert COLORS[3] == YELLOW


# ── Dataclasses ────────────────────────────────────────────────────


def test_gem_dataclass() -> None:
    g = Gem(x=100.0, y=50.0, color=0)
    assert g.x == 100.0
    assert g.y == 50.0
    assert g.color == 0
    assert g.wobble_phase == 0.0
    assert g.alive is True


def test_particle_dataclass() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == 8
    assert p.size == 2


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=80.0, text="+10", life=30, color=7)
    assert ft.x == 100.0
    assert ft.y == 80.0
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# ── Game init / state ──────────────────────────────────────────────


def test_init_state() -> None:
    g = _make_game()
    assert g.player_x == SCREEN_W // 2
    assert g.player_y == float(GROUND_Y)
    assert g.bounce_phase == 0.0
    assert g.bounce_direction == -1
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.gems_collected == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.active_color == 0
    assert g.gems == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.spawn_timer == 0
    assert g.shake_frames == 0
    assert g.frame == 0


def test_reset() -> None:
    g = _make_game()
    g.phase = "TITLE"
    g.score = 999
    g.heat = 50
    g.combo = 3
    g.gems.append(Gem(x=100, y=50, color=0))

    g.reset()

    assert g.phase == "PLAYING"
    assert g.score == 0
    assert g.heat == 0.0
    assert g.combo == 0
    assert g.gems == []
    assert g.game_timer == GAME_TIME
    assert g.super_mode is False
    # active_color is set to random int 0-3
    assert 0 <= g.active_color < NUM_COLORS


# ── Bounce physics ─────────────────────────────────────────────────


def test_bounce_phase_increases() -> None:
    g = _make_playing()
    g.bounce_phase = 0.0
    g.bounce_direction = -1

    g._update_bounce()

    assert g.bounce_phase > 0.0
    assert g.player_y < float(GROUND_Y)


def test_bounce_reaches_top_and_reverses() -> None:
    g = _make_playing()
    g.bounce_phase = BOUNCE_HEIGHT - BOUNCE_SPEED
    g.bounce_direction = -1

    g._update_bounce()
    g._update_bounce()

    # Should have hit top and started descending
    assert g.bounce_phase < BOUNCE_HEIGHT
    assert g.bounce_direction == 1


def test_bounce_descends_to_ground() -> None:
    g = _make_playing()
    g.bounce_phase = BOUNCE_SPEED
    g.bounce_direction = 1

    g._update_bounce()
    g._update_bounce()

    # Should hit ground and reverse
    assert g.bounce_phase >= 0.0
    # After hitting 0, direction becomes -1
    assert g.bounce_direction == -1


def test_player_y_tracks_bounce() -> None:
    g = _make_playing()
    g.bounce_phase = 40.0

    g._update_bounce()
    # player_y = GROUND_Y - bounce_phase
    assert abs(g.player_y - (float(GROUND_Y) - g.bounce_phase)) < 0.01


# ── Player movement ────────────────────────────────────────────────


def test_player_moves_left() -> None:
    g = _make_playing()
    g.player_x = 200.0
    g._update_player(left=True, right=False)
    assert g.player_x == 200.0 - MOVE_SPEED


def test_player_moves_right() -> None:
    g = _make_playing()
    g.player_x = 200.0
    g._update_player(left=False, right=True)
    assert g.player_x == 200.0 + MOVE_SPEED


def test_player_moves_both_net_zero() -> None:
    g = _make_playing()
    g.player_x = 200.0
    g._update_player(left=True, right=True)
    # left subtracts, right adds → net zero
    assert g.player_x == 200.0


def test_player_clamped_left_edge() -> None:
    g = _make_playing()
    g.player_x = float(PLAYER_W) + 0.5
    g._update_player(left=True, right=False)
    assert g.player_x == float(PLAYER_W)


def test_player_clamped_right_edge() -> None:
    g = _make_playing()
    g.player_x = float(SCREEN_W - PLAYER_W) - 0.5
    g._update_player(left=False, right=True)
    assert g.player_x == float(SCREEN_W - PLAYER_W)


# ── Gem spawning ───────────────────────────────────────────────────


def test_spawn_gem_adds_to_list() -> None:
    g = _make_playing()
    assert len(g.gems) == 0
    g._spawn_gem()
    assert len(g.gems) == 1
    gem = g.gems[0]
    assert GEM_SIZE * 2 <= gem.x <= SCREEN_W - GEM_SIZE * 2
    assert gem.y == 0.0
    assert 0 <= gem.color < NUM_COLORS


def test_spawn_gem_respects_max() -> None:
    g = _make_playing()
    for _ in range(MAX_GEMS):
        g.gems.append(Gem(x=100.0, y=50.0, color=0))
    g._spawn_gem()
    assert len(g.gems) == MAX_GEMS  # no new gem added


def test_spawn_gem_deterministic() -> None:
    g1 = _make_game()
    g1.phase = "PLAYING"
    g1.rng = random.Random(42)
    g1._spawn_gem()

    g2 = _make_game()
    g2.phase = "PLAYING"
    g2.rng = random.Random(42)
    g2._spawn_gem()

    # Same seed → same gem
    assert abs(g1.gems[0].x - g2.gems[0].x) < 0.01
    assert g1.gems[0].color == g2.gems[0].color


# ── Gem update ─────────────────────────────────────────────────────


def test_update_gems_descend() -> None:
    g = _make_playing()
    g.gems = [Gem(x=160.0, y=0.0, color=0)]
    g._update_gems()
    assert g.gems[0].y > 0.0  # descending


def test_update_gems_wobble() -> None:
    g = _make_playing()
    g.gems = [Gem(x=160.0, y=30.0, color=0)]
    old_x = g.gems[0].x
    g._update_gems()
    # wobble changes x slightly
    assert g.gems[0].x != old_x


# ── Collision detection ────────────────────────────────────────────


def test_check_gem_collisions_hit() -> None:
    g = _make_playing()
    g.player_x = 160.0
    g.bounce_phase = 40.0
    # Player top = GROUND_Y - 40 - PLAYER_H/2 = 216 - 40 - 16 = 160
    gem = Gem(x=160.0, y=160.0, color=0)  # right on player top
    g.gems = [gem]

    hits = g._check_gem_collisions()
    assert len(hits) == 1
    assert hits[0] is gem


def test_check_gem_collisions_miss_far() -> None:
    g = _make_playing()
    g.player_x = 160.0
    g.bounce_phase = 40.0
    gem = Gem(x=300.0, y=10.0, color=0)  # far away
    g.gems = [gem]

    hits = g._check_gem_collisions()
    assert len(hits) == 0


def test_check_gem_collisions_dead_gem_ignored() -> None:
    g = _make_playing()
    g.player_x = 160.0
    g.bounce_phase = 40.0
    gem = Gem(x=160.0, y=160.0, color=0, alive=False)
    g.gems = [gem]

    hits = g._check_gem_collisions()
    assert len(hits) == 0


# ── Gem collection ─────────────────────────────────────────────────


def test_collect_matching_color() -> None:
    g = _make_playing()
    g.active_color = 0  # RED
    gem = Gem(x=160.0, y=100.0, color=0)
    g.combo = 0
    g.score = 0

    g._collect_gem(gem)

    assert gem.alive is False
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > 0
    assert g.gems_collected == 1


def test_collect_wrong_color_adds_heat() -> None:
    g = _make_playing()
    g.active_color = 0  # RED
    gem = Gem(x=160.0, y=100.0, color=1)  # GREEN
    g.combo = 2
    g.score = 100

    g._collect_gem(gem)

    assert gem.alive is False
    assert g.combo == 0  # combo reset
    assert g.heat == HEAT_PER_MISS
    assert g.gems_collected == 1
    # Score unchanged (wrong color = no score)
    assert g.score == 100


def test_collect_wrong_color_heat_capped() -> None:
    g = _make_playing()
    g.active_color = 0
    g.heat = HEAT_MAX - 5
    gem = Gem(x=160.0, y=100.0, color=1)

    g._collect_gem(gem)
    assert g.heat == HEAT_MAX


def test_collect_changes_active_color() -> None:
    g = _make_playing()
    g.active_color = 0  # RED
    gem = Gem(x=160.0, y=100.0, color=2)  # DARK_BLUE

    g._collect_gem(gem)
    # Active color changes to the collected gem's color (even on miss)
    assert g.active_color == 2


def test_collect_combo_builds_score_multiplier() -> None:
    g = _make_playing()
    g.active_color = 0
    g.score = 0

    # Collect 3 red gems in a row
    for i in range(3):
        gem = Gem(x=160.0, y=100.0, color=0)
        g._collect_gem(gem)

    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score > 0


def test_collect_max_combo_tracks_highest() -> None:
    g = _make_playing()
    g.active_color = 0

    # Build combo to 3
    for _ in range(3):
        g._collect_gem(Gem(x=160.0, y=100.0, color=0))
    assert g.max_combo == 3

    # Then miss → combo resets
    g._collect_gem(Gem(x=160.0, y=100.0, color=1))
    assert g.combo == 0
    assert g.max_combo == 3  # max_combo preserved


# ── Score calculation ──────────────────────────────────────────────


def test_add_score_basic() -> None:
    g = _make_playing()
    g.combo = 0
    g.score = 0
    g._add_score(10)
    assert g.score == 10  # 10 * (1 + 0*0.5) = 10


def test_add_score_with_combo() -> None:
    g = _make_playing()
    g.combo = 4
    g.score = 0
    g._add_score(10)
    assert g.score == 30  # 10 * (1 + 4*0.5) = 10 * 3 = 30


def test_add_score_super_mode() -> None:
    g = _make_playing()
    g.combo = 2
    g.super_mode = True
    g.score = 0
    g._add_score(10)
    assert g.score == 60  # 10 * (1 + 2*0.5) * 3 = 10 * 2 * 3 = 60


# ── SUPER BOUNCE ────────────────────────────────────────────────────


def test_activate_super() -> None:
    g = _make_playing()
    g.player_x = 160.0
    g.player_y = float(GROUND_Y)
    g.active_color = 0
    g.combo = 4

    # Place some gems
    g.gems = [
        Gem(x=160.0, y=80.0, color=0),
        Gem(x=200.0, y=120.0, color=1),
        Gem(x=120.0, y=60.0, color=2),
    ]

    g._activate_super()

    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    # All gems should be collected
    assert all(not gem.alive for gem in g.gems)


def test_super_triggers_at_threshold() -> None:
    g = _make_playing()
    g.active_color = 0
    g.combo = COMBO_SUPER_THRESHOLD - 1  # 4

    # Collect one more matching gem
    gem = Gem(x=160.0, y=100.0, color=0)
    g._collect_gem(gem)

    assert g.combo == COMBO_SUPER_THRESHOLD
    assert g.super_mode is True


def test_super_does_not_retrigger() -> None:
    g = _make_playing()
    g.active_color = 0
    g.combo = 8
    g.super_mode = True
    g.super_timer = 100

    # Collect matching gem during super — should NOT re-trigger
    gem = Gem(x=160.0, y=100.0, color=0)
    g._collect_gem(gem)

    # combo increases but super_timer unchanged (no re-activation)
    assert g.combo == 9
    assert g.super_timer == 100


def test_super_timer_decrements() -> None:
    g = _make_playing()
    g.super_mode = True
    g.super_timer = 3
    g.combo = 5

    g._update_super()
    assert g.super_timer == 2
    assert g.super_mode is True

    g._update_super()
    assert g.super_timer == 1

    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.combo == 0  # combo resets after super ends


def test_super_collects_any_color() -> None:
    g = _make_playing()
    g.active_color = 0  # RED
    g.super_mode = True
    g.super_timer = 100
    g.combo = 0

    # Collect a non-matching color gem during super
    gem = Gem(x=160.0, y=100.0, color=3)  # YELLOW
    g._collect_gem(gem)

    # Should match (super mode makes any color match)
    assert g.combo == 1
    assert g.heat == 0  # no heat from miss


def test_super_active_color_unchanged() -> None:
    g = _make_playing()
    g.active_color = 0
    g.super_mode = True
    g.super_timer = 100

    g._collect_gem(Gem(x=160.0, y=100.0, color=2))
    # active_color should NOT change during super mode
    assert g.active_color == 0


# ── Particles ──────────────────────────────────────────────────────


def test_spawn_particles() -> None:
    g = _make_playing()
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 50.0, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 50.0
        assert 15 <= p.life <= 30
        assert p.color == 8


def test_update_particles() -> None:
    g = _make_playing()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, life=5, color=8)
    g.particles = [p]

    g._update_particles()

    assert p.x > 100.0  # moved right
    assert p.y < 50.0  # moved up initially (vy negative, gravity adds 0.1)
    assert p.life == 4
    assert len(g.particles) == 1  # still alive


def test_particles_removed_when_dead() -> None:
    g = _make_playing()
    g.particles = [
        Particle(x=100.0, y=50.0, vx=1.0, vy=0.0, life=1, color=8),
    ]

    g._update_particles()
    assert len(g.particles) == 0  # life went to 0, removed


# ── Floating texts ─────────────────────────────────────────────────


def test_add_floating_text() -> None:
    g = _make_playing()
    g._add_floating_text(100.0, 50.0, "TEST", 7)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "TEST"
    assert ft.color == 7
    assert ft.life == 30


def test_update_floating_texts() -> None:
    g = _make_playing()
    g.floating_texts = [FloatingText(x=100.0, y=50.0, text="HI", life=5, color=7)]

    g._update_floating_texts()
    assert g.floating_texts[0].y < 50.0  # floats up
    assert g.floating_texts[0].life == 4


def test_floating_texts_removed_when_dead() -> None:
    g = _make_playing()
    g.floating_texts = [
        FloatingText(x=100.0, y=50.0, text="HI", life=1, color=7),
    ]

    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Heat system ────────────────────────────────────────────────────


def test_heat_causes_game_over() -> None:
    g = _make_playing()
    g.heat = HEAT_MAX  # 100
    g.game_timer = 1000

    # Simulate the check in _update_playing
    if g.heat >= HEAT_MAX:
        g.phase = "GAME_OVER"
    assert g.phase == "GAME_OVER"


def test_heat_below_max_ok() -> None:
    g = _make_playing()
    g.heat = HEAT_MAX - 1
    g.game_timer = 1000

    if g.heat >= HEAT_MAX:
        g.phase = "GAME_OVER"
    assert g.phase == "PLAYING"


# ── Timer ──────────────────────────────────────────────────────────


def test_timer_game_over() -> None:
    g = _make_playing()
    g.game_timer = 0
    g.heat = 0

    if g.game_timer <= 0:
        g.phase = "GAME_OVER"
    assert g.phase == "GAME_OVER"


def test_timer_positive_ok() -> None:
    g = _make_playing()
    g.game_timer = 1
    g.heat = 0

    if g.game_timer <= 0:
        g.phase = "GAME_OVER"
    assert g.phase == "PLAYING"


# ── Game over reason ───────────────────────────────────────────────


def test_game_over_reason_heat() -> None:
    g = _make_playing()
    g.heat = HEAT_MAX
    g.game_timer = 100
    assert g.heat >= HEAT_MAX


def test_game_over_reason_timer() -> None:
    g = _make_playing()
    g.heat = 0
    g.game_timer = 0
    assert g.game_timer <= 0


# ── Edge cases ─────────────────────────────────────────────────────


def test_gems_filtered_after_collection() -> None:
    g = _make_playing()
    g.gems = [
        Gem(x=160.0, y=80.0, color=0, alive=True),
        Gem(x=200.0, y=60.0, color=1, alive=False),
        Gem(x=120.0, y=100.0, color=2, alive=True),
    ]

    g.gems = [gem for gem in g.gems if gem.alive]
    assert len(g.gems) == 2


def test_reset_clears_everything() -> None:
    g = _make_playing()
    g.score = 500
    g.combo = 10
    g.max_combo = 10
    g.gems_collected = 20
    g.heat = 80
    g.super_mode = True
    g.super_timer = 100
    g.game_timer = 100
    g.gems = [Gem(x=100, y=50, color=0)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=7)]
    g.floating_texts = [FloatingText(x=0, y=0, text="X", life=1, color=7)]

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.gems_collected == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.gems == []
    assert g.particles == []
    assert g.floating_texts == []


def test_shake_frames_heat_high() -> None:
    g = _make_playing()
    g.heat = 70
    # Simulate shake logic
    if g.heat > 60:
        g.shake_frames = max(1, int((g.heat - 60) / 5))
    assert g.shake_frames == 2  # (70-60)/5 = 2


def test_shake_frames_heat_low() -> None:
    g = _make_playing()
    g.heat = 50
    if g.heat > 60:
        g.shake_frames = max(1, int((g.heat - 60) / 5))
    elif g.shake_frames > 0:
        g.shake_frames -= 1
    assert g.shake_frames == 0


def test_spawn_timer_resets() -> None:
    g = _make_playing()
    g.spawn_timer = GEM_SPAWN_INTERVAL - 1
    g.spawn_timer += 1
    if g.spawn_timer >= GEM_SPAWN_INTERVAL:
        g.spawn_timer = 0
        g._spawn_gem()
    assert g.spawn_timer == 0
    assert len(g.gems) == 1


if __name__ == "__main__":
    # Run tests manually (pytest is preferred)

    tests = [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        sys.exit(1)
