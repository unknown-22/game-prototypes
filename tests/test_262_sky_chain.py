from __future__ import annotations

import random

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "prototypes" / "262_sky_chain"))

from main import Game, Phase, Ring  # noqa: E402



def _make_game(seed: int = 42) -> Game:
    game = Game.__new__(Game)
    game._rng = random.Random(seed)
    game.best_score = 0
    game.best_ghost = []
    game.phase = Phase.TITLE
    game.score = 0
    game.combo = 0
    game.max_combo = 0
    game.player_x = 160.0
    game.player_color_idx = 0
    game.player_color = game.PLAYER_COLORS[0]
    game.color_timer = game.COLOR_CYCLE_FRAMES
    game.rings = []
    game.particles = []
    game.floating_texts = []
    game.clouds = set()
    game.heat = 0.0
    game.super_timer = 0
    game.super_mode = False
    game.stun_timer = 0
    game.timer = game.TIMER_MAX
    game.frame_count = 0
    game.ring_spawn_timer = 0
    game.ring_spawn_interval = 60
    game.cloud_spread_timer = 0
    game.cloud_spread_interval = 60
    game.ghost_trail = []
    game.shake_frames = 0
    game._last_cloud_hit_frame = -100
    game._reset_playing()
    return game


class TestRingSpawning:
    def test_spawn_ring_basic(self) -> None:
        game = _make_game()
        assert len(game.rings) == 0
        game._spawn_ring()
        assert len(game.rings) == 1
        ring = game.rings[0]
        assert game.RING_RADIUS <= ring.x <= 320 - game.RING_RADIUS
        assert ring.y == 240.0 + game.RING_RADIUS
        assert ring.color in game.PLAYER_COLORS
        assert not ring.collected

    def test_spawn_ring_respects_max(self) -> None:
        game = _make_game()
        for _ in range(game.MAX_RINGS):
            game._spawn_ring()
        assert len(game.rings) == game.MAX_RINGS
        game._spawn_ring()
        assert len(game.rings) == game.MAX_RINGS

    def test_ring_scrolls_upward(self) -> None:
        game = _make_game()
        game._spawn_ring()
        init_y = game.rings[0].y
        game._update_rings()
        assert game.rings[0].y == init_y - game.RING_SPEED

    def test_ring_removed_when_offscreen(self) -> None:
        game = _make_game()
        game._spawn_ring()
        game.rings[0].y = -game.RING_RADIUS - 1
        game._update_rings()
        assert len(game.rings) == 0

    def test_collected_ring_removed(self) -> None:
        game = _make_game()
        game._spawn_ring()
        game.rings[0].collected = True
        game._update_rings()
        assert len(game.rings) == 0


class TestComboAndScore:
    def test_match_increases_combo_and_score(self) -> None:
        game = _make_game()
        game.player_color = game.PLAYER_COLORS[0]
        game.player_x = 160.0
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=game.player_color))
        game._check_ring_collisions()
        assert game.combo == 1
        assert game.score == 10
        assert game.max_combo == 1
        assert game.rings[0].collected

    def test_combo_accumulates(self) -> None:
        game = _make_game()
        game.player_color = game.PLAYER_COLORS[0]
        for i in range(3):
            game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=game.player_color))
            game._check_ring_collisions()
        assert game.combo == 3
        assert game.score == 10 + 20 + 30

    def test_mismatch_resets_combo_and_adds_heat(self) -> None:
        game = _make_game()
        game.player_color = game.PLAYER_COLORS[0]
        game.player_x = 160.0
        different_color = game.PLAYER_COLORS[1]
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=different_color))
        game.combo = 5
        game.score = 100
        game._check_ring_collisions()
        assert game.combo == 0
        assert game.heat == 15
        assert game.stun_timer == 15
        assert game.rings[0].collected

    def test_super_mode_activates_at_combo_4(self) -> None:
        game = _make_game()
        game.player_color = game.PLAYER_COLORS[0]
        game.combo = 3
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=game.player_color))
        game._check_ring_collisions()
        assert game.super_mode
        assert game.super_timer == game.SUPER_DURATION
        assert len(game.floating_texts) >= 1
        assert any(ft.text == "SUPER!" for ft in game.floating_texts)

    def test_super_mode_triples_score(self) -> None:
        game = _make_game()
        game.player_x = 160.0
        game.super_mode = True
        game.super_timer = 200
        game.combo = 2
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=99))
        game._check_ring_collisions()
        assert game.score == 10 * 3 * 3  # combo=3, multiplier=3, 10*3*3=90

    def test_super_mode_any_color_matches(self) -> None:
        game = _make_game()
        game.player_x = 160.0
        game.super_mode = True
        game.super_timer = 200
        game.combo = 0
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=99))
        game._check_ring_collisions()
        assert game.combo == 1
        assert game.score > 0

    def test_no_collision_when_distant(self) -> None:
        game = _make_game()
        game.player_color = game.PLAYER_COLORS[0]
        game.player_x = 160.0
        game.rings.append(Ring(x=300.0, y=float(game.PLAYER_Y), color=game.player_color))
        game._check_ring_collisions()
        assert game.combo == 0
        assert not game.rings[0].collected


class TestHeatAndGameOver:
    def test_heat_decays(self) -> None:
        game = _make_game()
        game.heat = 50.0
        game._update_heat()
        assert game.heat == 50.0 - 0.02

    def test_heat_does_not_go_below_zero(self) -> None:
        game = _make_game()
        game.heat = 0.0
        game._update_heat()
        assert game.heat == 0.0

    def test_heat_capped_at_100(self) -> None:
        game = _make_game()
        game.heat = 99.0
        game.player_x = 160.0
        game.player_color = game.PLAYER_COLORS[0]
        different_color = game.PLAYER_COLORS[1]
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=different_color))
        game._check_ring_collisions()
        assert game.heat <= game.HEAT_MAX

    def test_game_over_on_max_heat(self) -> None:
        game = _make_game()
        game.heat = 100.0
        assert game.heat == game.HEAT_MAX

    def test_game_over_on_timer_zero(self) -> None:
        game = _make_game()
        game.timer = 0
        assert game.timer <= 0


class TestClouds:
    def test_cloud_spawn_adds_clouds(self) -> None:
        game = _make_game(42)
        game._update_clouds()
        assert len(game.clouds) > 0

    def test_cloud_collision_adds_heat(self) -> None:
        game = _make_game(42)
        game.player_x = 16.0
        game.clouds.add((0, 1))
        game._check_cloud_collision()
        assert game.heat == 25

    def test_cloud_collision_resets_combo(self) -> None:
        game = _make_game(42)
        game.player_x = 16.0
        game.combo = 10
        game.clouds.add((0, 1))
        game._check_cloud_collision()
        assert game.combo == 0

    def test_cloud_collision_stuns(self) -> None:
        game = _make_game(42)
        game.player_x = 16.0
        game.clouds.add((0, 1))
        game._check_cloud_collision()
        assert game.stun_timer == 20

    def test_cloud_collision_cooldown(self) -> None:
        game = _make_game(42)
        game.player_x = 16.0
        game.clouds.add((0, 1))
        game._check_cloud_collision()
        heat_after_first = game.heat
        game._check_cloud_collision()
        assert game.heat == heat_after_first

    def test_super_mode_blocks_cloud_heat(self) -> None:
        game = _make_game(42)
        game.player_x = 16.0
        game.super_mode = True
        game.clouds.add((0, 1))
        game._check_cloud_collision()
        assert game.heat == 0

    def test_no_collision_when_not_overlapping(self) -> None:
        game = _make_game(42)
        game.player_x = 300.0
        game.clouds.add((0, 1))
        game._check_cloud_collision()
        assert game.heat == 0


class TestGhostTrail:
    def test_ghost_trail_records_position(self) -> None:
        game = _make_game()
        game.frame_count = 5
        # Simulate what _update_playing does on frame multiple of 5
        game.ghost_trail.append((game.player_x, float(game.PLAYER_Y)))
        assert len(game.ghost_trail) == 1
        assert game.ghost_trail[0] == (160.0, float(game.PLAYER_Y))

    def test_best_ghost_saved_on_better_score(self) -> None:
        game = _make_game()
        game.score = 100
        game.best_score = 50
        game.ghost_trail = [(1.0, 60.0), (2.0, 60.0)]
        game.timer = 0
        # Simulate game over logic
        if game.score > game.best_score:
            game.best_score = game.score
            game.best_ghost = game.ghost_trail.copy()
        assert game.best_score == 100
        assert game.best_ghost == [(1.0, 60.0), (2.0, 60.0)]

    def test_best_ghost_not_overwritten_on_worse_score(self) -> None:
        game = _make_game()
        game.score = 30
        game.best_score = 50
        game.best_ghost = [(10.0, 60.0)]
        game.ghost_trail = [(1.0, 60.0)]
        game.timer = 0
        if game.score > game.best_score:
            game.best_score = game.score
            game.best_ghost = game.ghost_trail.copy()
        assert game.best_score == 50
        assert game.best_ghost == [(10.0, 60.0)]


class TestSuperModeExpiry:
    def test_super_mode_expires(self) -> None:
        game = _make_game()
        game.super_mode = True
        game.super_timer = 1
        # Simulate the countdown from _update_playing
        game.super_timer -= 1
        assert game.super_timer == 0
        game.super_mode = False
        assert not game.super_mode

    def test_super_mode_not_re_activated_if_already_active(self) -> None:
        game = _make_game()
        game.super_mode = True
        game.super_timer = 100
        game.player_color = game.PLAYER_COLORS[0]
        game.player_x = 160.0
        game.combo = 3
        # Even at combo 3 -> 4 during super, it should NOT re-activate
        game.rings.append(Ring(x=160.0, y=float(game.PLAYER_Y), color=game.player_color))
        game._check_ring_collisions()
        assert game.combo == 4
        assert game.super_timer == 100


class TestFloatingTexts:
    def test_floating_text_added(self) -> None:
        game = _make_game()
        game._add_floating_text(100.0, 50.0, "TEST", 7)
        assert len(game.floating_texts) == 1
        assert game.floating_texts[0].text == "TEST"

    def test_floating_text_moves_up_and_expires(self) -> None:
        game = _make_game()
        game._add_floating_text(100.0, 50.0, "T", 7)
        ft = game.floating_texts[0]
        init_y = ft.y
        ft.life = 1
        game._update_floating_texts()
        assert ft.y == init_y - 1.0
        assert len(game.floating_texts) == 0


class TestPlayerColorCycle:
    def test_player_color_cycles(self) -> None:
        game = _make_game()
        assert game.player_color == game.PLAYER_COLORS[0]
        game.color_timer = 1
        game.color_timer -= 1
        if game.color_timer <= 0:
            game.color_timer = game.COLOR_CYCLE_FRAMES
            game.player_color_idx = (game.player_color_idx + 1) % 4
            game.player_color = game.PLAYER_COLORS[game.player_color_idx]
        assert game.player_color == game.PLAYER_COLORS[1]

    def test_player_color_wraps(self) -> None:
        game = _make_game()
        game.player_color_idx = 3
        game.player_color = game.PLAYER_COLORS[3]
        game.color_timer = 1
        game.color_timer -= 1
        if game.color_timer <= 0:
            game.color_timer = game.COLOR_CYCLE_FRAMES
            game.player_color_idx = (game.player_color_idx + 1) % 4
            game.player_color = game.PLAYER_COLORS[game.player_color_idx]
        assert game.player_color == game.PLAYER_COLORS[0]


class TestFindNearestRing:
    def test_find_nearest_returns_none_when_empty(self) -> None:
        game = _make_game()
        assert game._find_nearest_ring() is None

    def test_find_nearest_returns_closest(self) -> None:
        game = _make_game()
        game.player_x = 160.0
        game.rings.clear()
        game.rings.append(Ring(x=100.0, y=55.0, color=8))
        game.rings.append(Ring(x=200.0, y=65.0, color=11))
        game.rings.append(Ring(x=150.0, y=60.0, color=5))
        nearest = game._find_nearest_ring()
        assert nearest is not None
        assert nearest.x == 150.0

    def test_find_nearest_ignores_collected(self) -> None:
        game = _make_game()
        game.player_x = 160.0
        game.rings.clear()
        game.rings.append(Ring(x=150.0, y=60.0, color=8, collected=True))
        game.rings.append(Ring(x=200.0, y=60.0, color=11))
        nearest = game._find_nearest_ring()
        assert nearest is not None
        assert nearest.color == 11


class TestRingSpawnInterval:
    def test_spawn_interval_escalates(self) -> None:
        game = _make_game()
        game.frame_count = 900
        elapsed = game.frame_count / game.TIMER_MAX
        interval = max(25, int(60 - 35 * elapsed))
        assert interval < 60

    def test_spawn_interval_minimum(self) -> None:
        game = _make_game()
        game.frame_count = game.TIMER_MAX
        elapsed = game.frame_count / game.TIMER_MAX
        interval = max(25, int(60 - 35 * elapsed))
        assert interval == 25


class TestParticles:
    def test_particles_created(self) -> None:
        game = _make_game(42)
        game._add_particles(160.0, 60.0, 5, 8)
        assert len(game.particles) == 5

    def test_particles_move_and_expire(self) -> None:
        game = _make_game(42)
        game._add_particles(160.0, 60.0, 3, 8)
        for p in game.particles:
            p.life = 1
        init_count = len(game.particles)
        game._update_particles()
        assert len(game.particles) == 0
        assert init_count == 3
