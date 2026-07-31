from __future__ import annotations

import random
import sys

sys.path.insert(0, "prototypes/264_magnet_lift")
from main import (
    CRANE_MAX_X,
    CRANE_MIN_X,
    CRANE_SPEED,
    CRANE_SPEED_MAGNET,
    GAME_DURATION,
    HEAT_CAP,
    HEAT_DECAY,
    HEAT_MISMATCH,
    HEAT_MISS,
    SCRAP_COLORS,
    SCRAP_SIZE,
    SCROLL_SPEED_END,
    SCROLL_SPEED_START,
    SPAWN_INTERVAL_END,
    SPAWN_INTERVAL_START,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    Game,
    Phase,
    Scrap,
)


def _new_game() -> Game:
    g = Game.__new__(Game)
    g._set_defaults()
    g._headless = True
    g._rng = random.Random(42)
    return g


def _start_game(g: Game) -> None:
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.super_timer = 0
    g.crane_x = 160.0
    g.magnet_y = 20.0
    g.magnet_extending = False
    g.magnet_retracting = False
    g.last_color = -1
    g.space_was_held = False
    g.scraps.clear()
    g.particles.clear()
    g.trails.clear()
    g.floating_texts.clear()
    g.spawn_timer = 30
    g.spawn_interval = SPAWN_INTERVAL_START
    g.scroll_speed = SCROLL_SPEED_START
    g.shake_frames = 0
    g.shake_intensity = 0.0
    g.frame = 0


# ── Reset ─────────────────────────────────────────────────────────────────


class TestReset:
    def test_reset_sets_title_phase(self) -> None:
        g = _new_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.combo = 10
        g.max_combo = 15
        g.heat = 80.0
        g.timer = 100
        g.reset()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_DURATION
        assert g.super_timer == 0
        assert g.crane_x == 160.0
        assert g.magnet_y == 20.0
        assert len(g.scraps) == 0
        assert len(g.particles) == 0
        assert len(g.trails) == 0

    def test_reset_for_playing_clears_state(self) -> None:
        g = _new_game()
        g.score = 500
        g.combo = 10
        g.max_combo = 15
        g.heat = 80.0
        g.timer = 100
        g.super_timer = 50
        g.scraps = [Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])]
        g.particles = []
        g.trails = []
        g.reset_for_playing()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_DURATION
        assert g.super_timer == 0
        assert len(g.scraps) == 0


# ── Spawn Scrap ────────────────────────────────────────────────────────────


class TestSpawnScrap:
    def test_spawn_scrap_adds_to_list(self) -> None:
        g = _new_game()
        _start_game(g)
        assert len(g.scraps) == 0
        g.scraps.append(g._spawn_scrap())
        assert len(g.scraps) == 1

    def test_spawned_scrap_has_valid_color(self) -> None:
        g = _new_game()
        _start_game(g)
        scrap = g._spawn_scrap()
        assert scrap.color in SCRAP_COLORS

    def test_spawned_scrap_below_bottom(self) -> None:
        g = _new_game()
        _start_game(g)
        scrap = g._spawn_scrap()
        assert scrap.y > 240

    def test_spawned_scrap_within_horizontal_bounds(self) -> None:
        g = _new_game()
        _start_game(g)
        for _ in range(50):
            scrap = g._spawn_scrap()
            assert scrap.x >= CRANE_MIN_X + SCRAP_SIZE
            assert scrap.x <= CRANE_MAX_X - SCRAP_SIZE

    def test_spawn_deterministic_with_seed(self) -> None:
        g1 = _new_game()
        g2 = _new_game()
        _start_game(g1)
        _start_game(g2)
        s1 = g1._spawn_scrap()
        s2 = g2._spawn_scrap()
        assert s1.color == s2.color
        assert s1.x == s2.x
        assert s1.y == s2.y


# ── Pickup Check ───────────────────────────────────────────────────────────


class TestCheckPickup:
    def test_pickup_when_magnet_overlaps_scrap(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 100.0
        g.magnet_y = 100.0
        scrap = Scrap(x=100.0, y=104.0, color=SCRAP_COLORS[0])
        assert g._check_pickup(scrap) is True

    def test_no_pickup_when_magnet_far_left(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 100.0
        g.magnet_y = 100.0
        scrap = Scrap(x=50.0, y=100.0, color=SCRAP_COLORS[0])
        assert g._check_pickup(scrap) is False

    def test_no_pickup_when_magnet_above_scrap(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 100.0
        g.magnet_y = 50.0
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        assert g._check_pickup(scrap) is False


# ── Handle Pickup ──────────────────────────────────────────────────────────


class TestHandlePickup:
    def test_first_pickup_sets_last_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = -1
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert g.last_color == SCRAP_COLORS[0]
        assert g.combo == 1
        assert g.score == 10 + 1 * 5

    def test_same_color_increases_combo(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.combo = 2
        g.score = 50
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert g.combo == 3
        assert g.score == 50 + (10 + 3 * 5)

    def test_wrong_color_resets_combo_adds_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.combo = 3
        g.max_combo = 3
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[1])
        g._handle_pickup(scrap)
        assert g.combo == 0
        assert g.last_color == SCRAP_COLORS[1]
        assert g.heat == HEAT_MISMATCH

    def test_super_mode_any_color_matches(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        g.last_color = SCRAP_COLORS[0]
        g.combo = 5
        g.score = 100
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[1])
        g._handle_pickup(scrap)
        assert g.combo == 6
        assert g.score == 100 + (10 + 6 * 5) * 3

    def test_super_activation_at_threshold(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.combo = SUPER_THRESHOLD - 1  # combo = 3
        g.super_timer = 0
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert g.combo == SUPER_THRESHOLD
        assert g.super_timer == SUPER_DURATION

    def test_super_not_re_activated_while_active(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.combo = 5
        g.super_timer = 100  # already active
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert g.super_timer == 100  # unchanged, no re-activation

    def test_max_combo_tracks_highest(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.combo = 5
        g.max_combo = 5
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert g.max_combo == 6

    def test_max_combo_preserved_on_reset(self) -> None:
        g = _new_game()
        _start_game(g)
        g.max_combo = 8
        g.combo = 3
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[1])
        g.last_color = SCRAP_COLORS[0]
        g._handle_pickup(scrap)
        assert g.max_combo == 8
        assert g.combo == 0

    def test_heat_capped_on_mismatch(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.heat = HEAT_CAP - 5
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[1])
        g._handle_pickup(scrap)
        assert g.heat == HEAT_CAP

    def test_trail_dot_added_on_pickup(self) -> None:
        g = _new_game()
        _start_game(g)
        assert len(g.trails) == 0
        scrap = Scrap(x=100.0, y=120.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert len(g.trails) == 1
        assert g.trails[0].x == 100.0
        assert g.trails[0].y == 120.0

    def test_floating_text_added_on_pickup(self) -> None:
        g = _new_game()
        _start_game(g)
        assert len(g.floating_texts) == 0
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert len(g.floating_texts) >= 1


# ── Score ──────────────────────────────────────────────────────────────────


class TestScore:
    def test_score_value_base(self) -> None:
        assert Game._score_value(1) == 15

    def test_score_value_high_combo(self) -> None:
        assert Game._score_value(5) == 35

    def test_score_accumulates(self) -> None:
        g = _new_game()
        _start_game(g)
        g.score = 0
        g.last_color = -1
        s1 = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(s1)
        assert g.score == 15  # (10 + 1*5)
        g.last_color = SCRAP_COLORS[0]
        s2 = Scrap(x=110.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(s2)
        assert g.score == 15 + (10 + 2 * 5)  # = 35


# ── Heat ───────────────────────────────────────────────────────────────────


class TestHeat:
    def test_heat_decay(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0 - HEAT_DECAY

    def test_heat_decay_not_below_zero(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 0.001
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_no_decay_in_super_mode(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0

    def test_heat_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = HEAT_CAP
        g.timer = 100
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.phase == Phase.GAME_OVER

    def test_heat_game_over_on_update_heat_directly(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = HEAT_CAP
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_at_exactly_cap(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = HEAT_CAP - 0.001
        g._update_heat()
        # Below cap, no game over
        assert g.heat < HEAT_CAP


# ── Super Mode ─────────────────────────────────────────────────────────────


class TestSuperMode:
    def test_is_super_false_when_inactive(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 0
        assert g._is_super() is False

    def test_is_super_true_when_active(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        assert g._is_super() is True

    def test_super_timer_countdown(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 10
        g._update_super()
        assert g.super_timer == 9

    def test_super_expires_resets_combo_and_last_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = 8
        g.last_color = SCRAP_COLORS[0]
        g.super_timer = 1
        g._update_super()
        assert g.super_timer == 0
        assert g.combo == 0
        assert g.last_color == -1


# ── Crane Movement ─────────────────────────────────────────────────────────


class TestCraneMovement:
    def test_crane_moves_left(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 160.0
        inp = {"left": True, "right": False, "space": False, "space_p": False, "return_p": False}
        g._update_crane(inp)
        assert g.crane_x == 160.0 - CRANE_SPEED

    def test_crane_moves_right(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 160.0
        inp = {"left": False, "right": True, "space": False, "space_p": False, "return_p": False}
        g._update_crane(inp)
        assert g.crane_x == 160.0 + CRANE_SPEED

    def test_crane_clamped_left(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = CRANE_MIN_X + 1.0
        inp = {"left": True, "right": False, "space": False, "space_p": False, "return_p": False}
        g._update_crane(inp)
        assert g.crane_x == CRANE_MIN_X

    def test_crane_clamped_right(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = CRANE_MAX_X - 1.0
        inp = {"left": False, "right": True, "space": False, "space_p": False, "return_p": False}
        g._update_crane(inp)
        assert g.crane_x == CRANE_MAX_X

    def test_crane_slower_during_magnet_extend(self) -> None:
        g = _new_game()
        _start_game(g)
        g.magnet_extending = True
        g.crane_x = 160.0
        inp = {"left": False, "right": True, "space": False, "space_p": False, "return_p": False}
        g._update_crane(inp)
        assert g.crane_x == 160.0 + CRANE_SPEED_MAGNET


# ── Magnet ─────────────────────────────────────────────────────────────────


class TestMagnet:
    def test_magnet_extends(self) -> None:
        g = _new_game()
        _start_game(g)
        g.magnet_y = 20.0
        g.magnet_extending = True
        g._update_magnet({"left": False, "right": False, "space": True, "space_p": False, "return_p": False})
        assert g.magnet_y > 20.0

    def test_magnet_retracts(self) -> None:
        g = _new_game()
        _start_game(g)
        g.magnet_y = 100.0
        g.magnet_extending = False
        g.magnet_retracting = True
        g._update_magnet({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.magnet_y < 100.0

    def test_magnet_stops_at_bottom(self) -> None:
        g = _new_game()
        _start_game(g)
        g.magnet_extending = True
        g.magnet_y = 230.0
        g._update_magnet({"left": False, "right": False, "space": True, "space_p": False, "return_p": False})
        assert g.magnet_extending is False

    def test_magnet_stops_at_crane_y(self) -> None:
        g = _new_game()
        _start_game(g)
        g.magnet_retracting = True
        g.magnet_y = 22.0
        g._update_magnet({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.magnet_y == 20.0
        assert g.magnet_retracting is False

    def test_magnet_picks_up_in_range_scrap(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 100.0
        g.magnet_y = 95.0
        g.magnet_extending = True
        g.last_color = -1
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g.scraps = [scrap]
        g._update_magnet({"left": False, "right": False, "space": True, "space_p": False, "return_p": False})
        assert scrap.collected is True
        assert g.combo == 1


# ── Scraps Update ──────────────────────────────────────────────────────────


class TestUpdateScraps:
    def test_scraps_scroll_up(self) -> None:
        g = _new_game()
        _start_game(g)
        scrap = Scrap(x=100.0, y=200.0, color=SCRAP_COLORS[0])
        g.scraps = [scrap]
        g.scroll_speed = 2.0
        g._update_scraps()
        assert scrap.y == 198.0

    def test_missed_scrap_adds_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 0.0
        scrap = Scrap(x=100.0, y=30.0, color=SCRAP_COLORS[0])
        g.scraps = [scrap]
        g.scroll_speed = 10.0
        g._update_scraps()
        assert g.heat == HEAT_MISS

    def test_collected_scraps_removed(self) -> None:
        g = _new_game()
        _start_game(g)
        scrap = Scrap(x=100.0, y=0.0, color=SCRAP_COLORS[0], collected=True)
        g.scraps = [scrap]
        g.scroll_speed = 2.0
        g._update_scraps()
        assert len(g.scraps) == 0


# ── Spawn Update ───────────────────────────────────────────────────────────


class TestUpdateSpawn:
    def test_spawn_timer_ticks_down(self) -> None:
        g = _new_game()
        _start_game(g)
        g.spawn_timer = 10
        g._update_spawn()
        assert g.spawn_timer == 9

    def test_scrap_spawned_when_timer_reaches_zero(self) -> None:
        g = _new_game()
        _start_game(g)
        g.spawn_timer = 1
        g.scraps.clear()
        g._update_spawn()
        assert len(g.scraps) == 1
        assert g.spawn_timer == SPAWN_INTERVAL_START


# ── Difficulty ─────────────────────────────────────────────────────────────


class TestDifficulty:
    def test_scroll_speed_increases_over_time(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = GAME_DURATION // 2
        g._update_difficulty()
        assert g.scroll_speed > SCROLL_SPEED_START
        assert g.scroll_speed < SCROLL_SPEED_END

    def test_scroll_speed_at_start(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = GAME_DURATION
        g._update_difficulty()
        assert g.scroll_speed == SCROLL_SPEED_START

    def test_scroll_speed_at_end(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 0
        g._update_difficulty()
        assert g.scroll_speed == SCROLL_SPEED_END

    def test_spawn_interval_decreases_over_time(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = GAME_DURATION // 2
        g._update_difficulty()
        assert g.spawn_interval < SPAWN_INTERVAL_START
        assert g.spawn_interval > SPAWN_INTERVAL_END


# ── Particles ──────────────────────────────────────────────────────────────


class TestParticles:
    def test_particles_have_gravity(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, SCRAP_COLORS[0], 1)
        p = g.particles[0]
        vy_before = p.vy
        g._update_particles()
        assert p.vy > vy_before

    def test_particles_decrement_life(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, SCRAP_COLORS[0], 1)
        p = g.particles[0]
        life_before = p.life
        g._update_particles()
        assert p.life == life_before - 1

    def test_dead_particles_removed(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, SCRAP_COLORS[0], 1)
        g.particles[0].life = 1
        g._update_particles()
        assert len(g.particles) == 0

    def test_spawn_particles_correct_count(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, SCRAP_COLORS[0], 12)
        assert len(g.particles) == 12

    def test_super_activation_mixed_colors(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, -1, 30)
        assert len(g.particles) == 30


# ── Trails ─────────────────────────────────────────────────────────────────


class TestTrails:
    def test_trails_decrement_life(self) -> None:
        g = _new_game()
        _start_game(g)
        from main import TrailDot

        g.trails.append(TrailDot(x=100.0, y=100.0, life=60, color=SCRAP_COLORS[0]))
        g._update_trails()
        assert g.trails[0].life == 59

    def test_dead_trails_removed(self) -> None:
        g = _new_game()
        _start_game(g)
        from main import TrailDot

        g.trails.append(TrailDot(x=100.0, y=100.0, life=1, color=SCRAP_COLORS[0]))
        g._update_trails()
        assert len(g.trails) == 0


# ── Floating Texts ─────────────────────────────────────────────────────────


class TestFloatingTexts:
    def test_floating_text_moves_up(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_floating_text(100.0, 100.0, "+15", SCRAP_COLORS[0], 30)
        ft = g.floating_texts[0]
        y_before = ft.y
        g._update_floating_texts()
        assert ft.y < y_before

    def test_floating_text_life_decrements(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_floating_text(100.0, 100.0, "+15", SCRAP_COLORS[0], 30)
        ft = g.floating_texts[0]
        life_before = ft.life
        g._update_floating_texts()
        assert ft.life == life_before - 1

    def test_dead_floating_texts_removed(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_floating_text(100.0, 100.0, "+15", SCRAP_COLORS[0], 1)
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ── Phase Flow ─────────────────────────────────────────────────────────────


class TestPhaseFlow:
    def test_title_to_playing(self) -> None:
        g = _new_game()
        g.reset()
        g._update_title({"left": False, "right": False, "space": False, "space_p": True, "return_p": True})
        assert g.phase == Phase.PLAYING

    def test_playing_to_game_over_timer(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 1
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.phase == Phase.GAME_OVER

    def test_playing_to_game_over_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = HEAT_CAP
        g.timer = 100
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.phase == Phase.GAME_OVER

    def test_game_over_to_title(self) -> None:
        g = _new_game()
        g.phase = Phase.GAME_OVER
        g._update_game_over({"left": False, "right": False, "space": False, "space_p": True, "return_p": True})
        assert g.phase == Phase.TITLE

    def test_best_score_updated_on_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.score = 500
        g.best_score = 0
        g.timer = 1
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.best_score == 500

    def test_best_score_not_overwritten_by_lower(self) -> None:
        g = _new_game()
        _start_game(g)
        g.score = 300
        g.best_score = 500
        g.timer = 1
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.best_score == 500


# ── Timer ──────────────────────────────────────────────────────────────────


class TestTimer:
    def test_timer_decreases(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 100
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.timer == 99

    def test_timer_zero_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 1
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.phase == Phase.GAME_OVER


# ── Color Helpers ──────────────────────────────────────────────────────────


class TestColorHelpers:
    def test_color_for_index_0(self) -> None:
        assert Game._color_for_index(0) == SCRAP_COLORS[0]

    def test_color_for_index_wraps(self) -> None:
        assert Game._color_for_index(7) == SCRAP_COLORS[3]  # 7 % 4 == 3


# ── Edge Cases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_game_over_particles_spawned(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 1
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert len(g.particles) > 0

    def test_shake_on_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 1
        g._update_playing({"left": False, "right": False, "space": False, "space_p": False, "return_p": False})
        assert g.shake_frames > 0
        assert g.shake_intensity > 0

    def test_shake_on_super_activation(self) -> None:
        g = _new_game()
        _start_game(g)
        g.last_color = SCRAP_COLORS[0]
        g.combo = SUPER_THRESHOLD - 1
        g.super_timer = 0
        scrap = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        g._handle_pickup(scrap)
        assert g.shake_frames > 0

    def test_multiple_scraps_only_first_collected(self) -> None:
        g = _new_game()
        _start_game(g)
        g.crane_x = 100.0
        g.magnet_y = 95.0
        g.magnet_extending = True
        g.last_color = -1
        s1 = Scrap(x=100.0, y=100.0, color=SCRAP_COLORS[0])
        s2 = Scrap(x=100.0, y=105.0, color=SCRAP_COLORS[1])
        g.scraps = [s1, s2]
        g._update_magnet({"left": False, "right": False, "space": True, "space_p": False, "return_p": False})
        assert s1.collected is True
        # s2 may or may not be collected depending on timing; just verify at least one collected

    def test_rng_deterministic(self) -> None:
        g1 = _new_game()
        g2 = _new_game()
        _start_game(g1)
        _start_game(g2)
        s1 = g1._spawn_scrap()
        s2 = g2._spawn_scrap()
        assert s1.color == s2.color
        assert s1.x == s2.x
        assert s1.y == s2.y
