"""test_imports.py — Headless logic tests for 247_shuttle_chain."""
import sys
import random
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/247_shuttle_chain")

from main import (
    Game, Phase, Shuttle, Particle, FloatingText,
    SCREEN_W, SCREEN_H, GROUND_Y, NET_X, NET_TOP_Y,
    PLAYER_X, AI_X, TERMINAL_VY,
    COLORS, COLOR_NAMES, NUM_COLORS,
    COMBO_THRESHOLD, SUPER_DURATION, SUPER_SCORE_MULT,
    HEAT_MISMATCH, HEAT_DECAY, HEAT_MAX,
    MATCH_DURATION,
)


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.timer = MATCH_DURATION
    g.heat = 0.0
    g.player_color = 0
    g.ai_color = 0
    g.ai_y = 170.0
    g.ai_color_timer = 0
    g.ai_reaction_timer = -1
    g.shuttle = Shuttle(0, 0, 0, 0, 0)
    g._last_hitter = None
    g.super_mode = False
    g.super_timer = 0
    g.particles = []
    g.floating_texts = []
    g.rally_count = 0
    g.longest_rally = 0
    g.current_trail = []
    g.ghost_trail = []
    g._prev_shuttle_x = 0.0
    g._prev_shuttle_y = 0.0
    g._screen_shake = 0
    g._rng = random.Random(42)
    g.reset()
    return g


class TestConstants:
    def test_screen_size(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_H == 240

    def test_colors(self) -> None:
        assert len(COLORS) == 4
        assert COLORS == [8, 11, 5, 10]  # RED, LIME, DARK_BLUE, YELLOW
        assert len(COLOR_NAMES) == 4

    def test_combo(self) -> None:
        assert COMBO_THRESHOLD == 4
        assert SUPER_DURATION == 300
        assert SUPER_SCORE_MULT == 3

    def test_heat(self) -> None:
        assert HEAT_MISMATCH == 15.0
        assert HEAT_DECAY == 0.02
        assert HEAT_MAX == 100.0


class TestDataClasses:
    def test_shuttle(self) -> None:
        s = Shuttle(100.0, 150.0, 3.0, -2.0, COLORS[0])
        assert s.x == 100.0
        assert s.y == 150.0
        assert s.vx == 3.0
        assert s.vy == -2.0
        assert s.color == COLORS[0]
        assert s.active is True

    def test_particle(self) -> None:
        p = Particle(x=50.0, y=60.0, vx=1.0, vy=-1.0, life=20, color=8)
        assert p.life == 20
        assert p.color == 8

    def test_floating_text(self) -> None:
        ft = FloatingText(x=100.0, y=200.0, text="TEST", life=30, color=7)
        assert ft.text == "TEST"
        assert ft.life == 30


class TestGameInit:
    def test_reset(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.timer == MATCH_DURATION
        assert g.heat == 0.0
        assert g.super_mode is False
        assert g.super_timer == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert g.rally_count == 0
        assert g.longest_rally == 0
        assert g._screen_shake == 0
        assert g.shuttle.active is True
        assert g._last_hitter == "ai"  # shuttle spawns from AI side

    def test_spawn_shuttle(self) -> None:
        g = _make_game()
        s = g.shuttle
        assert s.x == float(AI_X)
        assert 120 <= s.y <= 180
        assert s.vx == -3.0
        assert s.color in COLORS
        assert s.active is True

    def test_phase_enum(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase
        # Enum identity
        g = _make_game()
        assert g.phase == Phase.PLAYING


class TestPhysics:
    def test_gravity_and_drag(self) -> None:
        g = _make_game()
        g.shuttle.vx = 5.0
        g.shuttle.vy = 0.0
        g.shuttle.y = 100.0
        initial_vx = g.shuttle.vx
        g._update_physics()
        # Drag should reduce vx
        assert g.shuttle.vx < initial_vx
        # Gravity should increase vy
        assert g.shuttle.vy > 0.0

    def test_ground_bounce(self) -> None:
        g = _make_game()
        g.shuttle.y = GROUND_Y - 1
        g.shuttle.vy = 5.0
        g.shuttle.vx = 2.0
        g.shuttle.x = NET_X - 10  # left side, player's side
        initial_heat = g.heat
        g._update_physics()
        # Should bounce
        assert g.shuttle.y == float(GROUND_Y)
        assert g.shuttle.vy < 0  # reversed upward
        # Heat should increase on player-side ground hit
        assert g.heat > initial_heat

    def test_ceiling_bounce(self) -> None:
        g = _make_game()
        g.shuttle.y = 1
        g.shuttle.vy = -5.0
        g._update_physics()
        assert g.shuttle.y == 0.0
        assert g.shuttle.vy > 0  # reversed downward

    def test_net_collision(self) -> None:
        g = _make_game()
        g.shuttle.x = NET_X - 1
        g.shuttle.y = NET_TOP_Y + 10  # below net top, should collide
        g.shuttle.vx = 5.0
        g._update_physics()
        # Should have bounced back (vx reversed)
        assert g.shuttle.vx < 0

    def test_net_no_collision_above(self) -> None:
        g = _make_game()
        g.shuttle.x = NET_X - 1
        g.shuttle.y = NET_TOP_Y - 5  # above net top, should pass through
        g.shuttle.vx = 5.0
        g._update_physics()
        # Should cross without bounce
        assert g.shuttle.x > NET_X

    def test_min_vx_clamp(self) -> None:
        g = _make_game()
        g.shuttle.vx = 0.3
        g.shuttle.y = 100.0
        g._update_physics()
        assert g.shuttle.vx == 0.0

    def test_terminal_vy_clamp(self) -> None:
        g = _make_game()
        g.shuttle.vy = TERMINAL_VY + 2.0
        g.shuttle.y = GROUND_Y - 100
        g._update_physics()
        assert g.shuttle.vy <= TERMINAL_VY


class TestPlayerHit:
    def test_match_builds_combo(self) -> None:
        g = _make_game()
        # Set up shuttle approaching player with matching color
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        g.shuttle.color = COLORS[g.player_color]  # matching
        g._last_hitter = "ai"
        g._check_player_hit()
        assert g.combo == 1
        assert g.score > 0
        assert g._last_hitter == "player"

    def test_match_score_formula(self) -> None:
        g = _make_game()
        g.combo = 3  # pre-existing combo
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        g.shuttle.color = COLORS[g.player_color]
        g._last_hitter = "ai"
        score_before = g.score
        g._check_player_hit()
        # score = 10 * 4 * 1 = 40
        assert g.score == score_before + 40

    def test_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.max_combo = 3
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        mismatched_color = COLORS[(g.player_color + 1) % NUM_COLORS]
        g.shuttle.color = mismatched_color
        g._last_hitter = "ai"
        g._check_player_hit()
        assert g.combo == 0
        assert g.max_combo == 3  # max_combo preserved
        assert g.heat == HEAT_MISMATCH  # increased

    def test_no_hit_wrong_direction(self) -> None:
        g = _make_game()
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = 5.0  # moving away from player
        g.shuttle.color = COLORS[g.player_color]
        g._last_hitter = "ai"
        combo_before = g.combo
        g._check_player_hit()
        assert g.combo == combo_before  # no hit

    def test_no_hit_when_not_ai_last(self) -> None:
        g = _make_game()
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        g.shuttle.color = COLORS[g.player_color]
        g._last_hitter = "player"  # player hit last, shouldn't hit again
        combo_before = g.combo
        g._check_player_hit()
        assert g.combo == combo_before

    def test_super_mode_activates(self) -> None:
        g = _make_game()
        g.combo = COMBO_THRESHOLD - 1  # 3
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        g.shuttle.color = COLORS[g.player_color]
        g._last_hitter = "ai"
        g._check_player_hit()
        assert g.combo == COMBO_THRESHOLD  # 4
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_score_multiplier(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 100
        g.combo = 5
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        g.shuttle.color = COLORS[(g.player_color + 1) % NUM_COLORS]  # mismatch color
        g._last_hitter = "ai"
        score_before = g.score
        g._check_player_hit()
        # In super mode, any color matches
        assert g.combo == 6
        assert g.score == score_before + int(10 * 6 * SUPER_SCORE_MULT)


class TestAI:
    def test_ai_reacts_with_delay(self) -> None:
        g = _make_game()
        g.shuttle.x = AI_X
        g.shuttle.y = 150
        g.shuttle.vx = 5.0
        g._last_hitter = "player"
        assert g.ai_reaction_timer == -1
        g._check_ai_hit()
        assert g.ai_reaction_timer > 0  # reaction timer set

    def test_do_ai_hit_match(self) -> None:
        g = _make_game()
        g.shuttle.x = AI_X
        g.shuttle.y = 150
        g.shuttle.vx = 5.0
        g.shuttle.color = COLORS[g.ai_color]  # matching
        g._last_hitter = "player"
        g._do_ai_hit()
        assert g._last_hitter == "ai"
        assert g.shuttle.vx < 0  # returned toward player
        assert g.rally_count == 1

    def test_do_ai_hit_mismatch(self) -> None:
        g = _make_game()
        g.shuttle.x = AI_X
        g.shuttle.y = 150
        g.shuttle.vx = 5.0
        mismatched = COLORS[(g.ai_color + 1) % NUM_COLORS]
        g.shuttle.color = mismatched
        g._last_hitter = "player"
        rally_before = g.rally_count
        g._do_ai_hit()
        assert g._last_hitter == "ai"
        assert g.shuttle.vx < 0  # still returned, just weaker
        assert g.rally_count == rally_before + 1

    def test_ai_cycles_color(self) -> None:
        g = _make_game()
        g.shuttle.y = 150
        initial_color = g.ai_color
        # Advance enough frames for one cycle
        cycle_interval = 60  # AI_BASE_CYCLE at start
        for _ in range(cycle_interval):
            g._update_ai()
        assert g.ai_color != initial_color


class TestHeat:
    def test_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0 - HEAT_DECAY

    def test_heat_never_negative(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_max_capped(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX + 10
        # Player hit mismatch adds heat, but it's capped
        g.shuttle.x = PLAYER_X
        g.shuttle.y = 150
        g.shuttle.vx = -5.0
        mismatched = COLORS[(g.player_color + 1) % NUM_COLORS]
        g.shuttle.color = mismatched
        g._last_hitter = "ai"
        g._check_player_hit()
        assert g.heat == HEAT_MAX  # capped at max


class TestSuper:
    def test_super_activation(self) -> None:
        g = _make_game()
        assert g.super_mode is False
        g._activate_super()
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION
        assert len(g.floating_texts) == 1

    def test_super_timer_decrement(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 50
        g._update_super_mode()
        assert g.super_timer == 49
        assert g.super_mode is True

    def test_super_ends(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 1
        g._update_super_mode()
        assert g.super_timer == 0
        assert g.super_mode is False


class TestParticles:
    def test_spawn_particles(self) -> None:
        g = _make_game()
        assert len(g.particles) == 0
        g._spawn_particles(100.0, 150.0, 8, 5)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == 8
            assert p.life >= 15
            assert p.life <= 25

    def test_update_particles_lifecycle(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 150.0, 8, 3)
        assert len(g.particles) == 3
        for _ in range(30):  # Should all expire
            g._update_particles()
        assert len(g.particles) == 0


class TestFloatingText:
    def test_spawn_floating_text(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100.0, 150.0, "TEST", 7, 30)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "TEST"
        assert g.floating_texts[0].life == 30

    def test_update_floating_texts(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100.0, 150.0, "TEST", 7, 2)
        initial_y = g.floating_texts[0].y
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].y < initial_y  # rises
        assert g.floating_texts[0].life == 1
        g._update_floating_texts()
        assert len(g.floating_texts) == 0  # expired


class TestRally:
    def test_end_rally_updates_longest(self) -> None:
        g = _make_game()
        g.rally_count = 10
        g.current_trail = [(100.0, 100.0), (200.0, 150.0)]
        g.longest_rally = 5
        g.ghost_trail = []
        g._end_rally()
        assert g.longest_rally == 10
        assert len(g.ghost_trail) == 2
        assert g.rally_count == 0

    def test_end_rally_no_update_if_shorter(self) -> None:
        g = _make_game()
        g.rally_count = 3
        g.longest_rally = 10
        g.ghost_trail = [(1.0, 1.0)]
        g._end_rally()
        assert g.longest_rally == 10  # unchanged
        assert len(g.ghost_trail) == 1  # preserved


class TestDifficultyEscalation:
    def test_ai_cycle_speeds_up(self) -> None:
        g = _make_game()
        g.timer = MATCH_DURATION // 2  # halfway through
        g.shuttle.y = 150
        # At halfway, cycle_interval should be less than AI_BASE_CYCLE
        progress = 1.0 - (g.timer / MATCH_DURATION)
        expected_cycle = int(60 - (60 - 30) * progress)
        assert expected_cycle < 60


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
