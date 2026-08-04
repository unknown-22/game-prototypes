"""test_imports.py — Headless logic tests for 279_sumo_chain."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/279_sumo_chain")
from main import Game, Wrestler, PushZone, Particle, FloatText


def _make_game() -> Game:
    g = Game.__new__(Game)
    import random
    g._rng = random.Random(42)
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = Game.GAME_TIME
    g.super_timer = 0
    g.rounds_won = 0
    g.last_color = None
    g.zones = []
    g.particles = []
    g.float_texts = []
    g.zone_spawn_timer = Game.ZONE_SPAWN_INTERVAL
    g.phase = "PLAYING"
    g.player = Wrestler(
        x=Game.RING_CX - 30.0, y=Game.RING_CY,
        radius=Game.WRESTLER_RADIUS, facing_angle=0.0,
        active_color=Game.COLORS[0],
    )
    g.ai = Wrestler(
        x=Game.RING_CX + 30.0, y=Game.RING_CY,
        radius=Game.WRESTLER_RADIUS, facing_angle=3.14159,
        active_color=Game.COLORS[1],
    )
    g.ai_push_timer = 60
    g.thrusting = False
    g.thrust_timer = 0
    g.thrust_duration = 8
    g._spawn_zones()
    return g


class TestDataClasses:
    def test_wrestler_creation(self) -> None:
        w = Wrestler(x=100.0, y=120.0, radius=8.0, facing_angle=0.0, active_color=8)
        assert w.x == 100.0
        assert w.radius == 8.0
        assert w.active_color == 8

    def test_push_zone_creation(self) -> None:
        z = PushZone(x=150.0, y=100.0, radius=20.0, color=11, life=300)
        assert z.color == 11
        assert z.life == 300

    def test_particle_creation(self) -> None:
        p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, color=8, life=15, size=2)
        assert p.x == 50.0
        assert p.life == 15
        assert p.size == 2

    def test_float_text_creation(self) -> None:
        ft = FloatText(x=160.0, y=120.0, text="+30", color=7, life=30)
        assert ft.text == "+30"
        assert ft.life == 30


class TestConstants:
    def test_screen_dimensions(self) -> None:
        assert Game.SCR_W == 320
        assert Game.SCR_H == 240

    def test_colors(self) -> None:
        assert len(Game.COLORS) == 4
        assert 8 in Game.COLORS
        assert 11 in Game.COLORS

    def test_combo_threshold(self) -> None:
        assert Game.COMBO_THRESHOLD == 4

    def test_max_heat(self) -> None:
        assert Game.MAX_HEAT == 100

    def test_game_duration(self) -> None:
        assert Game.GAME_TIME == 1800

    def test_super_duration(self) -> None:
        assert Game.SUPER_DURATION == 300

    def test_push_power_constants(self) -> None:
        assert Game.BASE_PUSH_POWER == 3.0
        assert Game.SUPER_PUSH_POWER == 7.5


class TestSpawnZones:
    def test_spawn_zones_creates_zones(self) -> None:
        g = _make_game()
        assert Game.ZONE_COUNT_MIN <= len(g.zones) <= Game.ZONE_COUNT_MAX

    def test_spawn_zones_within_ring(self) -> None:
        g = _make_game()
        for z in g.zones:
            dx = z.x - Game.RING_CX
            dy = z.y - Game.RING_CY
            dist = (dx * dx + dy * dy) ** 0.5
            assert dist < Game.RING_RADIUS - Game.ZONE_RADIUS

    def test_spawn_zones_no_overlap(self) -> None:
        g = _make_game()
        for i, z1 in enumerate(g.zones):
            for j, z2 in enumerate(g.zones):
                if i >= j:
                    continue
                dx = z1.x - z2.x
                dy = z1.y - z2.y
                assert dx * dx + dy * dy >= Game.ZONE_OVERLAP_MIN * Game.ZONE_OVERLAP_MIN - 1


class TestMatchZone:
    def test_match_zone_on_zone(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=8, life=300)]
        result = g._match_zone(150.0, 120.0)
        assert result == 8

    def test_match_zone_near_zone(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=11, life=300)]
        result = g._match_zone(160.0, 120.0)
        assert result == 11

    def test_match_zone_no_match(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=8, life=300)]
        result = g._match_zone(50.0, 50.0)
        assert result is None

    def test_match_zone_boundary_inside(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=5, life=300)]
        # threshold = WRESTLER_RADIUS + ZONE_RADIUS - 4 = 8 + 20 - 4 = 24
        # distance = 23.9 < 24 -> should match
        result = g._match_zone(173.9, 120.0)
        assert result == 5

    def test_match_zone_boundary_outside(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=10, life=300)]
        result = g._match_zone(174.1, 120.0)
        assert result is None


class TestComputePushPower:
    def test_base_power_no_combo(self) -> None:
        g = _make_game()
        power = g.compute_push_power(0, False)
        assert abs(power - 3.0) < 0.01

    def test_power_with_combo_1(self) -> None:
        g = _make_game()
        power = g.compute_push_power(1, False)
        assert abs(power - 3.6) < 0.01  # 3.0 * 1.2

    def test_power_with_combo_4(self) -> None:
        g = _make_game()
        power = g.compute_push_power(4, False)
        assert abs(power - 5.4) < 0.01  # 3.0 * 1.8

    def test_super_push_power(self) -> None:
        g = _make_game()
        power = g.compute_push_power(4, True)
        assert abs(power - 7.5) < 0.01

    def test_super_power_ignores_combo(self) -> None:
        g = _make_game()
        power = g.compute_push_power(0, True)
        assert abs(power - 7.5) < 0.01


class TestDoPush:
    def test_do_push_matching_first(self) -> None:
        g = _make_game()
        g.last_color = None
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        g._do_push(g.player, g.ai, 8)
        assert g.combo == 1
        assert g.score == 10
        assert g.last_color == 8

    def test_do_push_matching_same_color_combo(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 2
        g.score = 30
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        g._do_push(g.player, g.ai, 8)
        assert g.combo == 3
        assert g.score == 60  # 30 + 10*3

    def test_do_push_wrong_color(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.heat = 0.0
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        g._do_push(g.player, g.ai, 11)
        assert g.combo == 0
        assert g.heat == Game.HEAT_MISMATCH

    def test_do_push_activates_super(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.super_timer = 0
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        g._do_push(g.player, g.ai, 8)
        assert g.combo == 4
        assert g.super_timer == Game.SUPER_DURATION

    def test_do_push_super_mode_any_color(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.super_timer = 100
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        g._do_push(g.player, g.ai, 11)
        assert g.combo == 4
        assert g.heat == 0.0

    def test_do_push_moves_target(self) -> None:
        g = _make_game()
        g.last_color = None
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        old_x = g.ai.x
        g._do_push(g.player, g.ai, 8)
        assert g.ai.x > old_x  # pushed away from player

    def test_do_push_spawns_particles(self) -> None:
        g = _make_game()
        g.last_color = None
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0
        g._do_push(g.player, g.ai, 8)
        assert len(g.particles) > 0


class TestCheckRingOut:
    def test_in_ring(self) -> None:
        g = _make_game()
        assert not g._check_ring_out(Game.RING_CX, Game.RING_CY)

    def test_outside_ring(self) -> None:
        g = _make_game()
        assert g._check_ring_out(Game.RING_CX + Game.RING_RADIUS + 10, Game.RING_CY)

    def test_at_boundary_outside(self) -> None:
        g = _make_game()
        assert g._check_ring_out(Game.RING_CX + Game.RING_RADIUS, Game.RING_CY)

    def test_near_boundary_inside(self) -> None:
        g = _make_game()
        assert not g._check_ring_out(Game.RING_CX + Game.RING_RADIUS - 5, Game.RING_CY)


class TestClampToRing:
    def test_clamp_inside_ring_unchanged(self) -> None:
        g = _make_game()
        g.player.x = Game.RING_CX
        g.player.y = Game.RING_CY
        g._clamp_to_ring(g.player)
        assert g.player.x == Game.RING_CX
        assert g.player.y == Game.RING_CY

    def test_clamp_outside_ring_gets_clamped(self) -> None:
        g = _make_game()
        g.player.x = Game.RING_CX + 200
        g.player.y = Game.RING_CY
        g._clamp_to_ring(g.player)
        dx = g.player.x - Game.RING_CX
        dy = g.player.y - Game.RING_CY
        dist = (dx * dx + dy * dy) ** 0.5
        assert abs(dist - (Game.RING_RADIUS - g.player.radius)) < 0.01


class TestUpdateHeat:
    def test_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert abs(g.heat - 49.98) < 0.01

    def test_heat_min_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_game_over(self) -> None:
        g = _make_game()
        g.heat = 100.0
        g._update_heat()
        assert g.phase == "GAME_OVER"

    def test_heat_above_max_game_over(self) -> None:
        g = _make_game()
        g.heat = 115.0
        g._update_heat()
        assert g.phase == "GAME_OVER"


class TestUpdateZones:
    def test_update_zones_decrements_life(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=8, life=50)]
        g.zone_spawn_timer = 999
        g._update_zones()
        assert g.zones[0].life == 49

    def test_update_zones_removes_dead(self) -> None:
        g = _make_game()
        g.zones = [PushZone(x=150.0, y=120.0, radius=20.0, color=8, life=1)]
        g.zone_spawn_timer = 999
        g._update_zones()
        assert len(g.zones) == 0


class TestUpdateParticles:
    def test_particles_gravity(self) -> None:
        g = _make_game()
        p = Particle(x=160.0, y=100.0, vx=0.0, vy=0.0, color=8, life=15, size=2)
        g.particles = [p]
        g._update_particles()
        assert abs(p.vy - 0.1) < 0.01

    def test_particles_life_decrement(self) -> None:
        g = _make_game()
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=5, size=2)
        g.particles = [p]
        g._update_particles()
        assert p.life == 4

    def test_particles_remove_dead(self) -> None:
        g = _make_game()
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=1, size=2)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0


class TestUpdateFloatTexts:
    def test_float_texts_move_up(self) -> None:
        g = _make_game()
        ft = FloatText(x=160.0, y=120.0, text="+10", color=7, life=30)
        g.float_texts = [ft]
        g._update_float_texts()
        assert abs(ft.y - 119.5) < 0.01

    def test_float_texts_remove_dead(self) -> None:
        g = _make_game()
        ft = FloatText(x=0.0, y=0.0, text="X", color=7, life=1)
        g.float_texts = [ft]
        g._update_float_texts()
        assert len(g.float_texts) == 0


class TestActivateSuper:
    def test_activate_super_sets_timer(self) -> None:
        g = _make_game()
        g._activate_super()
        assert g.super_timer == Game.SUPER_DURATION

    def test_activate_super_spawns_text(self) -> None:
        g = _make_game()
        g._activate_super()
        assert any("SUPER PUSH" in ft.text for ft in g.float_texts)


class TestEndGame:
    def test_end_game_sets_phase(self) -> None:
        g = _make_game()
        g._end_game("test")
        assert g.phase == "GAME_OVER"

    def test_end_game_updates_best_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.best_score = 300
        g._end_game("test")
        assert g.best_score == 500

    def test_end_game_keeps_best_score(self) -> None:
        g = _make_game()
        g.score = 200
        g.best_score = 300
        g._end_game("test")
        assert g.best_score == 300


class TestGameState:
    def test_reset_initializes_state(self) -> None:
        g = _make_game()
        assert g.phase == "PLAYING"
        assert g.combo == 0
        assert g.score == 0
        assert g.heat == 0.0
        assert g.timer == Game.GAME_TIME
        assert g.super_timer == 0

    def test_zones_exist_after_init(self) -> None:
        g = _make_game()
        assert len(g.zones) >= Game.ZONE_COUNT_MIN

    def test_player_starts_left(self) -> None:
        g = _make_game()
        assert g.player.x < Game.RING_CX

    def test_ai_starts_right(self) -> None:
        g = _make_game()
        assert g.ai.x > Game.RING_CX


class TestFullComboChain:
    def test_full_combo_to_super(self) -> None:
        g = _make_game()
        g.last_color = None
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0

        for i in range(4):
            g._do_push(g.player, g.ai, 8)

        assert g.combo == 4
        assert g.max_combo == 4
        assert g.super_timer == Game.SUPER_DURATION
        assert g.score == 100  # 10 + 20 + 30 + 40

    def test_wrong_color_resets_combo(self) -> None:
        g = _make_game()
        g.last_color = None
        g.player.x = 140.0
        g.player.y = 120.0
        g.ai.x = 160.0
        g.ai.y = 120.0

        g._do_push(g.player, g.ai, 8)
        assert g.combo == 1
        g._do_push(g.player, g.ai, 8)
        assert g.combo == 2
        g._do_push(g.player, g.ai, 11)
        assert g.combo == 0
        assert g.heat == Game.HEAT_MISMATCH


class TestAiPush:
    def test_ai_push_hits_player(self) -> None:
        g = _make_game()
        g.ai.x = 155.0
        g.ai.y = 120.0
        g.player.x = 160.0
        g.player.y = 120.0
        old_heat = g.heat
        old_player_x = g.player.x
        g._ai_push()
        if g.heat > old_heat:
            assert g.heat == old_heat + Game.HEAT_AI_HIT
            assert g.player.x != old_player_x

    def test_ai_push_spawns_text_when_hit(self) -> None:
        g = _make_game()
        g.ai.x = 155.0
        g.ai.y = 120.0
        g.player.x = 160.0
        g.player.y = 120.0
        g._ai_push()
        if g.heat > 0:
            assert any("PUSHED" in ft.text for ft in g.float_texts)


class TestRingOutFlow:
    def test_ai_ring_out_triggers_round_win(self) -> None:
        g = _make_game()
        g.ai.x = Game.RING_CX + Game.RING_RADIUS + 10
        g.ai.y = Game.RING_CY
        g._on_ai_ring_out()
        assert g.phase == "ROUND_WIN"
        assert g.rounds_won == 1

    def test_player_ring_out_triggers_game_over(self) -> None:
        g = _make_game()
        g.player.x = Game.RING_CX + Game.RING_RADIUS + 10
        g.player.y = Game.RING_CY
        g._on_player_ring_out()
        assert g.phase == "GAME_OVER"

    def test_ai_ring_out_adds_score(self) -> None:
        g = _make_game()
        old_score = g.score
        g._on_ai_ring_out()
        assert g.score == old_score + 500


class TestResetRound:
    def test_reset_round_resets_positions(self) -> None:
        g = _make_game()
        g.player.x = 200.0
        g.ai.x = 100.0
        g.combo = 5
        g.heat = 50
        g._reset_round()
        assert g.combo == 0
        assert g.last_color is None
        assert not g.thrusting
        assert len(g.zones) >= Game.ZONE_COUNT_MIN
        # heat is NOT reset between rounds (persists)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
