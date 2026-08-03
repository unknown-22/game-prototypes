"""test_imports.py — Headless logic tests for 278_claw_chain."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/278_claw_chain")
from main import Game, Prize, Particle, FloatText


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = Game.GAME_DURATION
    g.super_timer = 0
    g.prizes = []
    g.particles = []
    g.float_texts = []
    g.spawn_timer = 0
    g.spawn_interval = 60
    g.phase = "PLAYING"
    g.claw_x = 160.0
    g.claw_dropping = False
    g.claw_drop_y = Game.CLAW_Y
    g.claw_retracting = False
    g.last_color = None
    g._init_prizes()
    return g


class TestPrize:
    def test_prize_creation(self) -> None:
        p = Prize(x=100.0, y=150.0, color=8)
        assert p.x == 100.0
        assert p.y == 150.0
        assert p.color == 8
        assert p.size == 8
        assert p.alive is True

    def test_prize_default_velocity(self) -> None:
        p = Prize(x=100.0, y=150.0, color=11)
        assert p.vx == 0.0
        assert p.vy == 0.0


class TestParticle:
    def test_particle_creation(self) -> None:
        p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, color=8, life=15)
        assert p.x == 50.0
        assert p.life == 15
        assert p.size == 2

    def test_particle_life_decrement(self) -> None:
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=10, life=3)
        p.life -= 1
        assert p.life == 2

    def test_particle_gravity(self) -> None:
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=10)
        p.vy += 0.1
        assert abs(p.vy - 0.1) < 0.01


class TestFloatText:
    def test_float_text_creation(self) -> None:
        ft = FloatText(x=160.0, y=120.0, text="+30", color=7, life=30)
        assert ft.text == "+30"
        assert ft.life == 30

    def test_float_text_life_decrement(self) -> None:
        ft = FloatText(x=0.0, y=0.0, text="X", color=7, life=5)
        ft.life -= 1
        assert ft.life == 4


class TestGameConstants:
    def test_screen_dimensions(self) -> None:
        assert Game.SCREEN_W == 320
        assert Game.SCREEN_H == 240

    def test_colors(self) -> None:
        assert len(Game.COLORS) == 4
        assert 8 in Game.COLORS  # RED
        assert 11 in Game.COLORS  # LIME

    def test_combo_threshold(self) -> None:
        assert Game.COMBO_THRESHOLD == 4

    def test_max_heat(self) -> None:
        assert Game.MAX_HEAT == 100

    def test_game_duration(self) -> None:
        assert Game.GAME_DURATION == 3600  # 60s

    def test_super_duration(self) -> None:
        assert Game.SUPER_DURATION == 300


class TestSpawnPrize:
    def test_spawn_prize_returns_valid(self) -> None:
        g = _make_game()
        g.timer = 3000  # mid-game
        p = g._spawn_prize()
        assert isinstance(p, Prize)
        assert 20 <= p.x <= 300
        assert 70 <= p.y <= 210
        assert p.color in Game.COLORS

    def test_spawn_prize_has_velocity(self) -> None:
        g = _make_game()
        g.timer = 3600  # start
        p = g._spawn_prize()
        assert abs(p.vx) <= 0.3 + 0.01
        assert abs(p.vy) <= 0.21 + 0.01


class TestInitPrizes:
    def test_init_prizes_fills_list(self) -> None:
        g = _make_game()
        assert len(g.prizes) == Game.PRIZE_COUNT

    def test_reset_clears_and_refills(self) -> None:
        g = _make_game()
        g._init_prizes()
        assert len(g.prizes) == Game.PRIZE_COUNT


class TestDriftSpeed:
    def test_drift_speed_start(self) -> None:
        g = _make_game()
        g.timer = Game.GAME_DURATION
        speed = g._drift_speed()
        assert abs(speed - 0.3) < 0.01

    def test_drift_speed_mid_game(self) -> None:
        g = _make_game()
        g.timer = Game.GAME_DURATION // 2
        speed = g._drift_speed()
        assert 0.45 <= speed <= 0.55

    def test_drift_speed_end(self) -> None:
        g = _make_game()
        g.timer = 0
        speed = g._drift_speed()
        assert abs(speed - 0.7) < 0.01


class TestSpawnInterval:
    def test_spawn_interval_start(self) -> None:
        g = _make_game()
        g.timer = Game.GAME_DURATION
        interval = g._spawn_interval_for_frame()
        assert interval == 60

    def test_spawn_interval_minimum(self) -> None:
        g = _make_game()
        g.timer = 0
        interval = g._spawn_interval_for_frame()
        assert interval == 30  # 60 - (3600//120) = 30


class TestCheckGrab:
    def test_check_grab_no_overlap(self) -> None:
        g = _make_game()
        g.claw_x = 160.0
        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=50.0, y=50.0, color=8)]
        result = g._check_grab()
        assert result is None

    def test_check_grab_overlap(self) -> None:
        g = _make_game()
        g.claw_x = 160.0
        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=160.0, y=100.0, color=8)]
        result = g._check_grab()
        assert result is not None
        assert result.color == 8

    def test_check_grab_close_overlap(self) -> None:
        g = _make_game()
        g.claw_x = 160.0
        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=168.0, y=100.0, color=11)]
        result = g._check_grab()
        assert result is not None  # distance 8 < radius 12

    def test_check_grab_boundary(self) -> None:
        g = _make_game()
        g.claw_x = 160.0
        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=171.0, y=100.0, color=5)]
        result = g._check_grab()
        assert result is not None  # distance 11 < radius 12

    def test_check_grab_super_radius(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.claw_x = 160.0
        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=178.0, y=100.0, color=10)]
        result = g._check_grab()
        assert result is not None  # distance 18 < radius 20

    def test_check_grab_skips_dead_prize(self) -> None:
        g = _make_game()
        g.claw_x = 160.0
        g.claw_drop_y = 100.0
        dead = Prize(x=160.0, y=100.0, color=8, alive=False)
        g.prizes = [dead]
        result = g._check_grab()
        assert result is None


class TestProcessGrab:
    def test_process_grab_first_grab(self) -> None:
        g = _make_game()
        g.last_color = None
        prize = Prize(x=160.0, y=100.0, color=8)
        gained = g._process_grab(prize)
        assert gained == 10  # 10 * 1 * 1
        assert g.combo == 1
        assert g.max_combo == 1
        assert g.last_color == 8
        assert g.score == 10

    def test_process_grab_same_color_combo(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.max_combo = 3
        g.score = 60
        prize = Prize(x=160.0, y=100.0, color=8)
        gained = g._process_grab(prize)
        assert gained == 40  # 10 * 4 * 1
        assert g.combo == 4
        assert g.max_combo == 4

    def test_process_grab_wrong_color(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.max_combo = 3
        g.heat = 0.0
        prize = Prize(x=160.0, y=100.0, color=11)
        gained = g._process_grab(prize)
        assert gained == 10  # base score only
        assert g.combo == 0
        assert g.last_color == 11
        assert g.heat == Game.HEAT_MISMATCH

    def test_process_grab_activates_super(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.max_combo = 3
        g.super_timer = 0
        prize = Prize(x=160.0, y=100.0, color=8)
        g._process_grab(prize)
        assert g.combo == 4
        assert g.super_timer == Game.SUPER_DURATION

    def test_process_grab_super_mode_any_color(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        g.super_timer = 100
        prize = Prize(x=160.0, y=100.0, color=11)  # different color
        gained = g._process_grab(prize)
        assert gained == 120  # 10 * 4 * 3
        assert g.combo == 4
        assert g.heat == 0  # no heat in super mode

    def test_process_grab_super_mode_multiplier(self) -> None:
        g = _make_game()
        g.last_color = None
        g.combo = 0
        g.super_timer = 100
        prize = Prize(x=160.0, y=100.0, color=10)
        gained = g._process_grab(prize)
        assert gained == 30  # 10 * 1 * 3

    def test_process_grab_spawns_particles(self) -> None:
        g = _make_game()
        g.last_color = None
        prize = Prize(x=160.0, y=100.0, color=8)
        g._process_grab(prize)
        assert len(g.particles) == 8  # normal grab

    def test_process_grab_spawns_super_particles(self) -> None:
        g = _make_game()
        g.last_color = None
        g.super_timer = 100
        prize = Prize(x=160.0, y=100.0, color=8)
        g._process_grab(prize)
        assert len(g.particles) == 16

    def test_process_grab_wrong_color_particles(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        prize = Prize(x=160.0, y=100.0, color=11)
        g._process_grab(prize)
        assert len(g.particles) == 4
        assert g.particles[0].color == 8  # RED miss particles

    def test_process_grab_floating_text(self) -> None:
        g = _make_game()
        g.last_color = None
        prize = Prize(x=160.0, y=100.0, color=8)
        g._process_grab(prize)
        assert len(g.float_texts) >= 1
        assert "+10" in g.float_texts[0].text

    def test_process_grab_combo_text_at_3(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 2
        prize = Prize(x=160.0, y=100.0, color=8)
        g._process_grab(prize)
        assert any("COMBO" in ft.text for ft in g.float_texts)

    def test_process_grab_wrong_spawns_wrong_text(self) -> None:
        g = _make_game()
        g.last_color = 8
        g.combo = 3
        prize = Prize(x=160.0, y=100.0, color=11)
        g._process_grab(prize)
        assert any("WRONG" in ft.text for ft in g.float_texts)


class TestRemovePrize:
    def test_remove_prize_reduces_and_replaces(self) -> None:
        g = _make_game()
        g.timer = 3000
        initial = len(g.prizes)
        target = g.prizes[0]
        g._remove_prize(target)
        assert target.alive is False
        assert len(g.prizes) == initial  # removed + new

    def test_remove_prize_new_prize_added(self) -> None:
        g = _make_game()
        g.timer = 3000
        target = g.prizes[0]
        g._remove_prize(target)
        assert target not in g.prizes


class TestUpdateHeat:
    def test_update_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert abs(g.heat - 49.98) < 0.01

    def test_update_heat_min_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_update_heat_game_over(self) -> None:
        g = _make_game()
        g.heat = 100.0
        g._update_heat()
        assert g.phase == "GAME_OVER"

    def test_update_heat_game_over_above_max(self) -> None:
        g = _make_game()
        g.heat = 115.0
        g._update_heat()
        assert g.phase == "GAME_OVER"


class TestUpdateSpawnTimer:
    def test_spawn_timer_decrements(self) -> None:
        g = _make_game()
        g.spawn_timer = 30
        g._update_spawn_timer()
        assert g.spawn_timer == 29

    def test_spawn_timer_resets_on_zero(self) -> None:
        g = _make_game()
        g.spawn_timer = 1
        g.timer = 3000
        g._update_spawn_timer()
        assert g.spawn_timer >= 25  # should have reset
        assert g.spawn_timer <= 60


class TestUpdatePrizes:
    def test_update_prizes_moves(self) -> None:
        g = _make_game()
        prize = Prize(x=160.0, y=150.0, color=8, vx=1.0, vy=0.5)
        g.prizes = [prize]
        g._update_prizes()
        assert abs(prize.x - 161.0) < 0.01
        assert abs(prize.y - 150.5) < 0.01

    def test_update_prizes_wrap_horizontal(self) -> None:
        g = _make_game()
        prize = Prize(x=310.0, y=150.0, color=8, vx=2.0, vy=0.0)
        g.prizes = [prize]
        g._update_prizes()
        assert prize.x <= 20  # wrapped from 312 to 15

    def test_update_prizes_wrap_vertical(self) -> None:
        g = _make_game()
        prize = Prize(x=160.0, y=Game.BIN_BOTTOM - 3, color=8, vx=0.0, vy=5.0)
        g.prizes = [prize]
        g._update_prizes()
        assert prize.y <= Game.BIN_TOP + 10


class TestUpdateParticles:
    def test_update_particles_gravity(self) -> None:
        g = _make_game()
        p = Particle(x=160.0, y=100.0, vx=0.0, vy=0.0, color=8, life=15)
        g.particles = [p]
        g._update_particles()
        assert abs(p.vy - 0.1) < 0.01

    def test_update_particles_life_decrement(self) -> None:
        g = _make_game()
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=5)
        g.particles = [p]
        g._update_particles()
        assert p.life == 4

    def test_update_particles_remove_dead(self) -> None:
        g = _make_game()
        p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=1)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0


class TestUpdateFloatTexts:
    def test_update_float_texts_moves_up(self) -> None:
        g = _make_game()
        ft = FloatText(x=160.0, y=120.0, text="+10", color=7, life=30)
        g.float_texts = [ft]
        g._update_float_texts()
        assert abs(ft.y - 119.5) < 0.01

    def test_update_float_texts_remove_dead(self) -> None:
        g = _make_game()
        ft = FloatText(x=0.0, y=0.0, text="X", color=7, life=1)
        g.float_texts = [ft]
        g._update_float_texts()
        assert len(g.float_texts) == 0


class TestEndGame:
    def test_end_game_sets_phase(self) -> None:
        g = _make_game()
        g._end_game()
        assert g.phase == "GAME_OVER"

    def test_end_game_updates_best_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.best_score = 300
        g._end_game()
        assert g.best_score == 500

    def test_end_game_keeps_best_score(self) -> None:
        g = _make_game()
        g.score = 200
        g.best_score = 300
        g._end_game()
        assert g.best_score == 300


class TestActivateSuper:
    def test_activate_super_sets_timer(self) -> None:
        g = _make_game()
        g._activate_super()
        assert g.super_timer == Game.SUPER_DURATION

    def test_activate_super_spawns_text(self) -> None:
        g = _make_game()
        g._activate_super()
        assert any("SUPER CLAW" in ft.text for ft in g.float_texts)


class TestGameState:
    def test_reset_initializes_state(self) -> None:
        g = _make_game()
        assert g.phase == "PLAYING"
        assert g.claw_x == 160.0
        assert g.combo == 0
        assert g.score == 0
        assert g.heat == 0.0
        assert g.timer == Game.GAME_DURATION
        assert g.super_timer == 0

    def test_make_game_has_prizes(self) -> None:
        g = _make_game()
        assert len(g.prizes) == Game.PRIZE_COUNT

    def test_claw_limits(self) -> None:
        g = _make_game()
        g.claw_x = 0.0
        # Clamp via the limits
        clamped = max(Game.CLAW_LEFT_LIMIT, min(g.claw_x, Game.CLAW_RIGHT_LIMIT))
        assert clamped == Game.CLAW_LEFT_LIMIT


class TestFullGrabCycle:
    def test_grab_cycle_combo_building(self) -> None:
        g = _make_game()
        g.timer = 3000
        g.claw_x = 160.0
        g.claw_drop_y = 100.0

        prizes = [
            Prize(x=160.0, y=100.0, color=8),
            Prize(x=160.0, y=120.0, color=8),
            Prize(x=160.0, y=140.0, color=8),
            Prize(x=160.0, y=160.0, color=8),
        ]
        g.prizes = prizes

        # First grab
        result = g._check_grab()
        assert result is not None
        g._process_grab(result)
        g._remove_prize(result)
        assert g.combo == 1
        assert g.score == 10

        # Second grab (same color)
        g.claw_drop_y = 120.0
        result = g._check_grab()
        assert result is not None
        g._process_grab(result)
        g._remove_prize(result)
        assert g.combo == 2
        assert g.score == 30  # 10 + 20

        # Third grab (same color)
        g.claw_drop_y = 140.0
        result = g._check_grab()
        assert result is not None
        g._process_grab(result)
        g._remove_prize(result)
        assert g.combo == 3
        assert g.score == 60  # 30 + 30

        # Fourth grab (same color -> SUPER)
        g.claw_drop_y = 160.0
        result = g._check_grab()
        assert result is not None
        g._process_grab(result)
        g._remove_prize(result)
        assert g.combo == 4
        assert g.super_timer == Game.SUPER_DURATION
        assert g.score >= 60  # score increased

    def test_grab_cycle_wrong_color_reset(self) -> None:
        g = _make_game()
        g.timer = 3000
        g.claw_x = 160.0
        g.last_color = 8
        g.combo = 3
        g.score = 60
        g.max_combo = 3

        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=160.0, y=100.0, color=11)]  # different color

        result = g._check_grab()
        assert result is not None
        g._process_grab(result)
        assert g.combo == 0
        assert g.heat == Game.HEAT_MISMATCH
        assert g.last_color == 11

    def test_grab_cycle_reaches_game_over_by_heat(self) -> None:
        g = _make_game()
        g.timer = 3000
        g.claw_x = 160.0
        g.last_color = 8
        g.combo = 3
        g.heat = 99.0

        g.claw_drop_y = 100.0
        g.prizes = [Prize(x=160.0, y=100.0, color=11)]  # wrong color

        result = g._check_grab()
        assert result is not None
        g._process_grab(result)
        assert g.heat == 99.0 + Game.HEAT_MISMATCH  # 114
        g._update_heat()
        assert g.phase == "GAME_OVER"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
