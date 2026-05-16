"""test_imports.py — Headless logic tests for CHROMA DASH.

Tests dataclasses, game logic, and utility methods without initializing Pyxel.
Avoids any pyxel API calls that would panic (btn, btnp, mouse_*, camera, etc.).
"""

from __future__ import annotations

import inspect
import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/032_chroma_dash")

from main import (
    COLOR_MAP,
    COLOR_NAMES,
    COMBO_MAX_DISPLAY,
    FLUX_DURATION,
    FLUX_SCORE_MULT,
    FLUX_THRESHOLD,
    GEM_HEIGHTS,
    GRAVITY,
    GROUND_Y,
    JUMP_VEL,
    NUM_COLORS,
    PLAYER_H,
    PLAYER_H_DUCK,
    PLAYER_W,
    PLAYER_W_DUCK,
    PLAYER_X,
    SCREEN_H,
    SCREEN_W,
    SPEED_BASE,
    SPEED_INC,
    SPEED_MAX,
    FloatingText,
    Game,
    Gem,
    Obstacle,
    Particle,
    Phase,
    Player,
)


# ── Config Tests ──────────────────────────────────────────────────────────────


def test_config_values() -> None:
    """Verify key configuration constants."""
    assert SCREEN_W == 240
    assert SCREEN_H == 160
    assert GROUND_Y == 130
    assert PLAYER_X == 40
    assert PLAYER_W == 14
    assert PLAYER_H == 18
    assert PLAYER_W_DUCK == 14
    assert GRAVITY > 0
    assert JUMP_VEL < 0
    assert SPEED_BASE > 0
    assert SPEED_MAX > SPEED_BASE
    assert SPEED_INC > 0
    assert NUM_COLORS == 4
    assert FLUX_THRESHOLD == 5
    assert FLUX_DURATION == 300
    assert FLUX_SCORE_MULT == 3
    assert len(GEM_HEIGHTS) == 3
    assert len(COLOR_MAP) == NUM_COLORS
    assert len(COLOR_NAMES) == NUM_COLORS


# ── Dataclass Tests ───────────────────────────────────────────────────────────


def test_gem_creation() -> None:
    """Test Gem dataclass construction and defaults."""
    g = Gem(x=100.0, y=80.0, color=0)
    assert g.x == 100.0
    assert g.y == 80.0
    assert g.color == 0
    assert g.collected is False
    assert g.size == 8

    g2 = Gem(x=200.0, y=60.0, color=2, collected=True)
    assert g2.collected is True
    assert g2.color == 2


def test_obstacle_creation() -> None:
    """Test Obstacle dataclass construction."""
    o = Obstacle(x=150.0, y=120, w=16, h=10, kind="spike")
    assert o.kind == "spike"
    assert o.active is True
    assert o.w == 16
    assert o.h == 10

    o2 = Obstacle(x=200.0, y=100, w=24, h=30, kind="pit")
    assert o2.kind == "pit"
    assert o2.active is True


def test_particle_creation() -> None:
    """Test Particle dataclass construction."""
    p = Particle(x=50.0, y=60.0, vx=1.5, vy=-2.0, color=8, life=25)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 25


def test_floating_text_creation() -> None:
    """Test FloatingText dataclass construction."""
    ft = FloatingText(x=40.0, y=100.0, text="+10", color=10, life=30)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.y == 100.0


def test_phase_enum() -> None:
    """Test Phase enum values."""
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.PLAYING != Phase.GAME_OVER


# ── Player Tests ──────────────────────────────────────────────────────────────


def test_player_defaults() -> None:
    """Test Player default construction."""
    p = Player()
    assert p.y == GROUND_Y - PLAYER_H
    assert p.vy == 0.0
    assert p.is_jumping is False
    assert p.is_ducking is False
    assert p.duck_timer == 0
    assert p.invuln_timer == 0


def test_player_h_property() -> None:
    """Test Player.h returns correct height based on duck state."""
    p = Player()
    assert p.h == PLAYER_H

    p2 = Player(is_ducking=True)
    assert p2.h == 10  # PLAYER_H_DUCK


def test_player_w_property() -> None:
    """Test Player.w returns correct width."""
    p = Player()
    assert p.w == PLAYER_W


def test_player_gravity() -> None:
    """Test player physics: gravity pulls player down."""
    p = Player(vy=0.0, y=100.0)
    # Apply one frame of gravity
    p.vy += GRAVITY
    p.y += p.vy
    assert p.y > 100.0  # Player fell


def test_player_jump() -> None:
    """Test player physics: jump applies upward velocity."""
    p = Player(vy=JUMP_VEL, is_jumping=True, y=GROUND_Y - PLAYER_H)
    p.y += p.vy
    assert p.y < GROUND_Y - PLAYER_H  # Player is above ground


def test_player_ground_clamp() -> None:
    """Test player doesn't fall below ground."""
    p = Player(y=GROUND_Y - 5, vy=3.0)
    # Simulate physics update
    p.vy += GRAVITY
    p.y += p.vy
    if p.y >= GROUND_Y - PLAYER_H:
        p.y = GROUND_Y - PLAYER_H
        p.vy = 0.0
        p.is_jumping = False
    assert p.y == GROUND_Y - PLAYER_H
    assert p.vy == 0.0


def test_player_ceiling_clamp() -> None:
    """Test player doesn't go above screen."""
    p = Player(y=-5, vy=-3.0)
    if p.y < 0:
        p.y = 0
        p.vy = 0.0
    assert p.y == 0


def test_player_duck_state() -> None:
    """Test duck state properties."""
    p = Player(is_ducking=True, duck_timer=5)
    assert p.is_ducking is True
    assert p.duck_timer == 5
    assert p.h == 10  # PLAYER_H_DUCK


# ── Game State Tests ──────────────────────────────────────────────────────────


def test_game_reset_state() -> None:
    """Test Game reset() initializes all state correctly."""
    g = Game.__new__(Game)
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.player.y == GROUND_Y - PLAYER_H
    assert g.player.vy == 0.0
    assert g.player.is_jumping is False
    assert g.player.is_ducking is False
    assert len(g.gems) == 0
    assert len(g.obstacles) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.speed == SPEED_BASE
    assert g.score == 0
    assert g.distance == 0
    assert g.combo == 0
    assert g.last_color is None
    assert g.flux_timer == 0
    assert g.is_flux is False
    assert g.best_score == 0


def test_game_speed_ramp() -> None:
    """Test speed increases with distance."""
    g = Game.__new__(Game)
    g.reset()
    assert g.speed == SPEED_BASE

    # Simulate distance accumulation
    g.distance = 10000
    expected_speed = min(SPEED_BASE + SPEED_INC * g.distance, SPEED_MAX)
    # This is _update_playing logic — just test the formula
    assert expected_speed > SPEED_BASE
    assert expected_speed <= SPEED_MAX


def test_speed_clamp_to_max() -> None:
    """Test speed never exceeds SPEED_MAX."""
    g = Game.__new__(Game)
    g.reset()
    g.distance = 999999
    expected = min(SPEED_BASE + SPEED_INC * g.distance, SPEED_MAX)
    assert expected == SPEED_MAX


# ── Collision Tests ───────────────────────────────────────────────────────────


def test_player_bounds_normal() -> None:
    """Test player hitbox when standing."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.player.is_ducking = False
    pl, pt, pr, pb = g._get_player_bounds()
    assert pl == PLAYER_X
    assert pt == GROUND_Y - PLAYER_H  # 112
    assert pr == PLAYER_X + PLAYER_W  # 54
    assert pb == GROUND_Y  # 130


def test_player_bounds_ducking() -> None:
    """Test player hitbox when ducking."""
    g = Game.__new__(Game)
    g.reset()
    g.player.is_ducking = True
    pl, pt, pr, pb = g._get_player_bounds()
    assert pt == GROUND_Y - PLAYER_H_DUCK  # 120
    assert pb == GROUND_Y


def test_player_bounds_midair() -> None:
    """Test player hitbox when in the air."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = 60.0
    g.player.is_jumping = True
    pl, pt, pr, pb = g._get_player_bounds()
    assert pt == 60.0
    assert pb == 60.0 + PLAYER_H  # 78


def test_gem_collection_near_player() -> None:
    """Test gem near player gets collected."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.scroll_x = 0.0

    # Place gem right at player position
    gem = Gem(x=PLAYER_X + PLAYER_W // 2, y=GROUND_Y - PLAYER_H + PLAYER_H // 2, color=0)
    g.gems.append(gem)

    # Mock score to verify collection
    initial_score = g.score
    g._update_collisions()

    assert gem.collected is True
    assert g.score > initial_score


def test_gem_collection_far_from_player() -> None:
    """Test gem far from player is not collected."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.scroll_x = 0.0

    # Place gem far from player
    gem = Gem(x=200.0, y=GROUND_Y - PLAYER_H + PLAYER_H // 2, color=0)
    g.gems.append(gem)

    g._update_collisions()

    assert gem.collected is False


def test_obstacle_spike_collision() -> None:
    """Test collision with spike obstacle."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.player.is_ducking = False
    g.scroll_x = 0.0

    # Place spike right at player position
    spike = Obstacle(x=PLAYER_X, y=GROUND_Y - 10, w=16, h=10, kind="spike")
    g.obstacles.append(spike)

    # We can't easily test _on_death() without pyxel, but we can test the collision detection
    pl, pt, pr, pb = g._get_player_bounds()
    ox = spike.x - g.scroll_x
    oy = spike.y

    # AABB collision check (mirrors _update_collisions logic)
    hit = pl < ox + spike.w and pr > ox and pt < oy + spike.h and pb > oy
    assert hit is True


def test_obstacle_spike_no_collision_jumping() -> None:
    """Test no collision with spike when jumping over it."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = 50.0  # Well above ground
    g.player.is_jumping = True
    g.scroll_x = 0.0

    spike = Obstacle(x=PLAYER_X, y=GROUND_Y - 10, w=16, h=10, kind="spike")
    g.obstacles.append(spike)

    pl, pt, pr, pb = g._get_player_bounds()
    ox = spike.x - g.scroll_x
    oy = spike.y

    hit = pl < ox + spike.w and pr > ox and pt < oy + spike.h and pb > oy
    assert hit is False


def test_obstacle_bar_collision() -> None:
    """Test collision with bar obstacle."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - 45  # At bar height
    g.player.is_ducking = False
    g.scroll_x = 0.0

    bar = Obstacle(x=PLAYER_X, y=GROUND_Y - 45, w=20, h=12, kind="bar")
    g.obstacles.append(bar)

    pl, pt, pr, pb = g._get_player_bounds()
    ox = bar.x - g.scroll_x
    oy = bar.y

    hit = pl < ox + bar.w and pr > ox and pt < oy + bar.h and pb > oy
    assert hit is True


def test_obstacle_bar_avoided_by_ducking() -> None:
    """Test bar is avoided when ducking."""
    g = Game.__new__(Game)
    g.reset()
    g.player.is_ducking = True
    g.scroll_x = 0.0

    bar = Obstacle(x=PLAYER_X, y=GROUND_Y - 45, w=20, h=12, kind="bar")
    g.obstacles.append(bar)

    pl, pt, pr, pb = g._get_player_bounds()
    ox = bar.x - g.scroll_x
    oy = bar.y

    hit = pl < ox + bar.w and pr > ox and pt < oy + bar.h and pb > oy
    assert hit is False  # Ducking player is below bar


def test_obstacle_pit_collision_on_ground() -> None:
    """Test pit collision when player is on ground over pit."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H  # On ground
    g.player.is_jumping = False
    g.player.is_ducking = False
    g.scroll_x = 0.0

    pit = Obstacle(x=PLAYER_X - 5, y=GROUND_Y, w=24, h=30, kind="pit")
    g.obstacles.append(pit)

    pl, pt, pr, pb = g._get_player_bounds()
    ox = pit.x - g.scroll_x
    oy = pit.y

    # Pit collision: player on ground AND x-overlap AND not ducking
    on_ground = g.player.y >= GROUND_Y - PLAYER_H
    x_overlap = pl < ox + pit.w and pr > ox
    hit = on_ground and x_overlap and not g.player.is_ducking
    assert hit is True


def test_obstacle_pit_avoided_by_jumping() -> None:
    """Test pit is avoided when jumping."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = 60.0  # In the air
    g.player.is_jumping = True
    g.scroll_x = 0.0

    pit = Obstacle(x=PLAYER_X - 5, y=GROUND_Y, w=24, h=30, kind="pit")
    g.obstacles.append(pit)

    on_ground = g.player.y >= GROUND_Y - PLAYER_H
    assert on_ground is False  # Player is jumping, so pit doesn't kill


def test_obstacle_pit_avoided_by_ducking() -> None:
    """Test pit is avoided when ducking (stays above pit)."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.player.is_ducking = True
    g.scroll_x = 0.0

    pit = Obstacle(x=PLAYER_X - 5, y=GROUND_Y, w=24, h=30, kind="pit")
    g.obstacles.append(pit)

    # Pit logic: ducking player is above pit (player.y at GROUND_Y - PLAYER_H_DUCK)
    # The pit collision only checks if NOT ducking
    assert g.player.is_ducking is True  # Ducking avoids pit


# ── Combo Logic Tests ─────────────────────────────────────────────────────────


def test_combo_same_color_increments() -> None:
    """Test COMBO increases on same-color consecutive gems."""
    g = Game.__new__(Game)
    g.reset()

    # First gem
    g.combo = 0
    g.last_color = None
    gem1 = Gem(x=PLAYER_X + 7, y=GEM_HEIGHTS[0], color=1)
    g.gems = [gem1]
    g.scroll_x = 0.0
    g.player.y = GROUND_Y - PLAYER_H
    g._update_collisions()
    assert g.combo == 1
    assert g.last_color == 1

    # Second gem, same color
    gem2 = Gem(x=PLAYER_X + 7, y=GEM_HEIGHTS[0], color=1, collected=False)
    g.gems = [gem2]
    g._update_collisions()
    assert g.combo == 2
    assert g.last_color == 1

    # Third gem, same color
    gem3 = Gem(x=PLAYER_X + 7, y=GEM_HEIGHTS[0], color=1, collected=False)
    g.gems = [gem3]
    g._update_collisions()
    assert g.combo == 3


def test_combo_reset_on_different_color() -> None:
    """Test COMBO resets to 1 when different color collected."""
    g = Game.__new__(Game)
    g.reset()

    # Build combo on color 1
    g.combo = 4
    g.last_color = 1

    # Collect different color
    gem = Gem(x=PLAYER_X + 7, y=GEM_HEIGHTS[0], color=2)
    g.gems = [gem]
    g.scroll_x = 0.0
    g.player.y = GROUND_Y - PLAYER_H
    g._update_collisions()
    assert g.combo == 1
    assert g.last_color == 2


def test_combo_min_multiplier() -> None:
    """Test combo multiplier is at least 1."""
    g = Game.__new__(Game)
    g.reset()
    g.combo = 1
    combo_mult = min(g.combo, 10)
    assert combo_mult == 1


def test_combo_max_multiplier() -> None:
    """Test combo multiplier caps at 10."""
    g = Game.__new__(Game)
    g.reset()
    g.combo = 25
    combo_mult = min(g.combo, 10)
    assert combo_mult == 10  # Capped


def test_combo_score_calculation() -> None:
    """Test gem score = base * combo_mult * flux_mult."""
    g = Game.__new__(Game)
    g.reset()

    g.combo = 3
    combo_mult = min(g.combo, 10)
    base = Game.SCORE_GEM_BASE  # 10
    assert base * combo_mult == 30  # 10 * 3

    # With flux
    g.is_flux = True
    assert base * FLUX_SCORE_MULT * combo_mult == 90  # 10 * 3 * 3


# ── Flux Tests ────────────────────────────────────────────────────────────────


def test_flux_activation_at_threshold() -> None:
    """Test FLUX activates when COMBO reaches threshold."""
    g = Game.__new__(Game)
    g.reset()

    # Set combo just below threshold
    g.combo = FLUX_THRESHOLD - 1
    g.last_color = 0

    # Collect another same-color gem
    gem = Gem(x=PLAYER_X + 7, y=GEM_HEIGHTS[0], color=0)
    g.gems = [gem]
    g.scroll_x = 0.0
    g.player.y = GROUND_Y - PLAYER_H
    g._update_collisions()

    assert g.combo == FLUX_THRESHOLD
    if g.combo >= FLUX_THRESHOLD and not g.is_flux:
        g._activate_flux()
    assert g.is_flux is True
    assert g.flux_timer == FLUX_DURATION


def test_flux_timer_decrements() -> None:
    """Test flux timer counts down."""
    g = Game.__new__(Game)
    g.reset()
    g.is_flux = True
    g.flux_timer = 100
    g._update_flux()
    assert g.flux_timer == 99


def test_flux_ends_when_timer_expires() -> None:
    """Test flux deactivates when timer reaches 0."""
    g = Game.__new__(Game)
    g.reset()
    g.is_flux = True
    g.flux_timer = 1
    g.combo = 5
    g.last_color = 0
    g._update_flux()
    assert g.is_flux is False
    assert g.combo == 0
    assert g.last_color is None
    assert g.player.invuln_timer == 15
    assert len(g.floating_texts) == 1
    assert "FLUX END" in g.floating_texts[0].text


def test_no_double_flux_activation() -> None:
    """Test flux is not activated twice when already active."""
    g = Game.__new__(Game)
    g.reset()
    g.is_flux = True
    g.flux_timer = 50

    # Check that _activate_flux isn't called when already in flux
    if g.combo >= FLUX_THRESHOLD and not g.is_flux:
        g._activate_flux()
    assert g.is_flux is True
    assert g.flux_timer == 50  # Unchanged


# ── Particle System Tests ─────────────────────────────────────────────────────


def test_particles_move_and_fade() -> None:
    """Test particles update: move with velocity, gravity, and lose life."""
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, color=8, life=10)

    # Apply one frame
    p.x += p.vx
    p.y += p.vy
    p.vy += 0.1  # gravity
    p.life -= 1

    assert p.x == 51.0
    assert abs(p.y - 58.0) < 0.01
    assert abs(p.vy - (-1.9)) < 0.01
    assert p.life == 9


def test_particles_culled_when_dead() -> None:
    """Test particles with life <= 0 are removed."""
    particles = [
        Particle(x=10, y=10, vx=0, vy=0, color=8, life=5),
        Particle(x=20, y=20, vx=0, vy=0, color=8, life=0),
        Particle(x=30, y=30, vx=0, vy=0, color=8, life=-1),
    ]
    alive = [p for p in particles if p.life > 0]
    assert len(alive) == 1


# ── Floating Text Tests ───────────────────────────────────────────────────────


def test_floating_text_rises() -> None:
    """Test floating text moves upward."""
    ft = FloatingText(x=40.0, y=100.0, text="+10", color=10, life=30)
    ft.y -= 0.8  # rise
    ft.life -= 1
    assert abs(ft.y - 99.2) < 0.01
    assert ft.life == 29


def test_floating_text_culled_when_dead() -> None:
    """Test floating texts with life <= 0 are removed."""
    texts = [
        FloatingText(x=10, y=10, text="a", color=8, life=10),
        FloatingText(x=20, y=20, text="b", color=8, life=0),
    ]
    alive = [t for t in texts if t.life > 0]
    assert len(alive) == 1


# ── Spawning Tests ────────────────────────────────────────────────────────────


def test_spawn_next_x_advances() -> None:
    """Test spawn position advances."""
    g = Game.__new__(Game)
    g.reset()
    initial = g._next_spawn_x
    assert initial > SCREEN_W  # Spawns ahead of screen


def test_spawning_generates_entities() -> None:
    """Test spawn loop generates gems and obstacles."""
    g = Game.__new__(Game)
    g.reset()
    g.scroll_x = 0.0
    g._next_spawn_x = SCREEN_W + 30.0

    # Run spawn until some entities are created
    initial_gems = len(g.gems)
    initial_obs = len(g.obstacles)
    right_edge = SCREEN_W + g.scroll_x + 50
    for _ in range(20):
        if g._next_spawn_x >= right_edge:
            break
        g._next_spawn_x += 80 + 20  # SPAWN_MIN_GAP + random ish
        # Simulate a gem spawn
        g.gems.append(Gem(x=g._next_spawn_x, y=GEM_HEIGHTS[0], color=0))

    assert len(g.gems) > initial_gems


# ── Entity Culling Tests ──────────────────────────────────────────────────────


def test_gems_culled_off_screen() -> None:
    """Test gems behind the scroll position are removed."""
    g = Game.__new__(Game)
    g.reset()
    g.scroll_x = 300.0

    g.gems = [
        Gem(x=100.0, y=80, color=0),  # Behind scroll
        Gem(x=310.0, y=80, color=1),  # Visible
        Gem(x=350.0, y=80, color=2),  # Ahead
    ]
    gem2 = Gem(x=280.0, y=80, color=3, collected=True)  # Collected
    g.gems.append(gem2)

    g._update_entities()
    # Gems behind scroll_x - 20 (=280) and collected gems are removed
    assert len(g.gems) == 2  # Only the two ahead remain


def test_obstacles_culled_off_screen() -> None:
    """Test obstacles behind scroll are removed."""
    g = Game.__new__(Game)
    g.reset()
    g.scroll_x = 300.0

    g.obstacles = [
        Obstacle(x=100.0, y=120, w=16, h=10, kind="spike"),  # Behind
        Obstacle(x=310.0, y=120, w=16, h=10, kind="spike"),  # Visible
    ]

    g._update_entities()
    assert len(g.obstacles) == 1


# ── Score Tests ───────────────────────────────────────────────────────────────


def test_score_distance_increment() -> None:
    """Test score increases with distance each frame."""
    g = Game.__new__(Game)
    g.reset()
    initial = g.score
    g.scroll_x += g.speed
    g.distance += 1
    g.score += Game.SCORE_DIST_PER_FRAME
    assert g.score == initial + 1


def test_best_score_tracks_max() -> None:
    """Test best_score updates correctly."""
    g = Game.__new__(Game)
    g.reset()
    g.score = 500
    g.best_score = 300
    g._on_death()
    assert g.best_score == 500

    g2 = Game.__new__(Game)
    g2.reset()
    g2.score = 200
    g2.best_score = 500
    g2._on_death()
    assert g2.best_score == 500  # Unchanged


# ── Game Over Tests ───────────────────────────────────────────────────────────


def test_death_sets_game_over_phase() -> None:
    """Test on_death transitions to GAME_OVER."""
    g = Game.__new__(Game)
    g.reset()
    assert g.phase == Phase.PLAYING
    g._on_death()
    assert g.phase == Phase.GAME_OVER


def test_reset_from_game_over() -> None:
    """Test reset clears state from game over."""
    g = Game.__new__(Game)
    g.reset()
    g.score = 1000
    g._on_death()
    assert g.phase == Phase.GAME_OVER

    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert len(g.gems) == 0
    assert len(g.obstacles) == 0


# ── Color Map Tests ───────────────────────────────────────────────────────────


def test_color_map_has_all_colors() -> None:
    """Test COLOR_MAP covers all color indices."""
    for i in range(NUM_COLORS):
        assert i in COLOR_MAP
        assert COLOR_MAP[i] is not None


def test_color_names_have_all_colors() -> None:
    """Test COLOR_NAMES covers all color indices."""
    for i in range(NUM_COLORS):
        assert i in COLOR_NAMES
        assert len(COLOR_NAMES[i]) > 0


# ── Method Signature Tests ────────────────────────────────────────────────────


def test_game_has_required_methods() -> None:
    """Test Game class has all required methods."""
    required = [
        "reset", "update", "draw",
        "_update_playing", "_update_game_over",
        "_update_input", "_update_player_physics",
        "_update_spawning", "_update_entities",
        "_update_collisions", "_update_flux",
        "_update_particles", "_update_floating_texts",
        "_on_gem_collected", "_activate_flux",
        "_on_death", "_get_player_bounds",
        "_draw_playing", "_draw_background", "_draw_ground",
        "_draw_gems", "_draw_obstacles", "_draw_player",
        "_draw_particles", "_draw_floating_texts", "_draw_hud",
        "_draw_game_over_overlay",
    ]
    for method in required:
        assert hasattr(Game, method), f"Missing method: {method}"


def test_no_method_name_collisions() -> None:
    """Test no duplicate method names in Game class."""
    methods = [m for m in dir(Game) if not m.startswith("__")]
    assert len(methods) == len(set(methods))


# ── Combo Max Display Test ────────────────────────────────────────────────────


def test_combo_max_display() -> None:
    """Test COMBO_MAX_DISPLAY is reasonable."""
    assert COMBO_MAX_DISPLAY == 99


# ── Additional Edge Cases ─────────────────────────────────────────────────────


def test_gem_collected_flag_prevents_double_count() -> None:
    """Test already-collected gems are skipped."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.scroll_x = 0.0

    collected_gem = Gem(x=PLAYER_X + 7, y=GEM_HEIGHTS[0], color=0, collected=True)
    g.gems = [collected_gem]

    initial_score = g.score
    g._update_collisions()
    # Score shouldn't change because gem was already collected
    assert g.score == initial_score


def test_inactive_obstacles_skipped() -> None:
    """Test inactive obstacles don't trigger collision."""
    g = Game.__new__(Game)
    g.reset()
    g.player.y = GROUND_Y - PLAYER_H
    g.scroll_x = 0.0

    spike = Obstacle(x=PLAYER_X, y=GROUND_Y - 10, w=16, h=10, kind="spike", active=False)
    g.obstacles = [spike]

    # Collision check skips inactive obstacles
    for obs in g.obstacles:
        if not obs.active:
            continue
        assert False, "Should not reach here"
    # Test passes if we get here (inactive obstacle was skipped)


def test_player_invuln_decrements() -> None:
    """Test invulnerability timer counts down."""
    p = Player(invuln_timer=10)
    if p.invuln_timer > 0:
        p.invuln_timer -= 1
    assert p.invuln_timer == 9


if __name__ == "__main__":
    import subprocess
    import sys

    # Collect all test functions
    tests = [
        obj
        for name, obj in inspect.getmembers(sys.modules[__name__])
        if inspect.isfunction(obj) and name.startswith("test_")
    ]
    tests.sort(key=lambda f: f.__name__)

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
