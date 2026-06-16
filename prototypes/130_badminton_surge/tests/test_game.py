"""Headless tests for Badminton Surge."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (  # noqa: E402
    AI_X,
    COLORS,
    COMBO_THRESHOLD,
    DRAG,
    GAME_DURATION,
    GRAVITY,
    HEAT_DECAY,
    HEAT_PER_MISS,
    HEAT_PER_WRONG_COLOR,
    HIT_POWER_X,
    HIT_POWER_Y_BASE,
    PLAYER_X,
    RACKET_H,
    SCREEN_W,
    SUPER_DURATION,
    FloatingText,
    Game,
    GhostTrail,
    Particle,
    Phase,
    Shuttlecock,
)


# ------------------------------------------------------------------
# Test helper
# ------------------------------------------------------------------
def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.player_y = 120.0
    g.player_racket_color = 0
    g.ai_y = 120.0
    g.shuttlecock = None
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.game_timer = GAME_DURATION
    g.phase = Phase.PLAYING
    g.particles = []
    g.floating_texts = []
    g.ghost_trail = []
    g.shake_frames = 0
    g.rally_count = 0
    g.last_hit_color = -1
    g._swing_timer = 0
    g._trail_record = []
    g._ghost_bonus_collected = False
    g._serve_timer = 40
    g._racket_color_timer = 90
    g.reset()
    g.phase = Phase.PLAYING
    return g


# ------------------------------------------------------------------
# Test: Constants
# ------------------------------------------------------------------
class TestConstants:
    def test_screen_dimensions(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_W > 0

    def test_gravity_and_drag_positive(self) -> None:
        assert GRAVITY > 0
        assert 0 < DRAG < 1

    def test_hit_power(self) -> None:
        assert HIT_POWER_X > 0
        assert HIT_POWER_Y_BASE < 0  # upward launch

    def test_combo_threshold(self) -> None:
        assert COMBO_THRESHOLD >= 2

    def test_super_duration(self) -> None:
        assert SUPER_DURATION > 0

    def test_colors_count(self) -> None:
        assert len(COLORS) == 4


# ------------------------------------------------------------------
# Test: Shuttlecock physics
# ------------------------------------------------------------------
class TestShuttlecockPhysics:
    def test_gravity_increases_vy(self) -> None:
        g = _make_game()
        sc = Shuttlecock(x=150.0, y=100.0, vx=2.0, vy=-4.0, color=0)
        vy_before = sc.vy
        g._update_shuttlecock(sc)
        assert sc.vy > vy_before, "Gravity should increase vy"

    def test_drag_reduces_velocity(self) -> None:
        g = _make_game()
        sc = Shuttlecock(x=150.0, y=100.0, vx=3.0, vy=-3.0, color=0)
        vx_before = sc.vx
        vy_before = sc.vy
        g._update_shuttlecock(sc)
        assert abs(sc.vx) < abs(vx_before), "Drag should reduce vx magnitude"
        assert sc.vy > vy_before, "vy increases from gravity, but may be smaller than initial due to drag"

    def test_shuttlecock_moves(self) -> None:
        g = _make_game()
        sc = Shuttlecock(x=100.0, y=100.0, vx=2.0, vy=1.0, color=0)
        g._update_shuttlecock(sc)
        assert sc.x != 100.0
        assert sc.y != 100.0

    def test_bounce_off_top(self) -> None:
        g = _make_game()
        sc = Shuttlecock(x=150.0, y=2.0, vx=1.0, vy=-5.0, color=0)
        g._update_shuttlecock(sc)
        assert sc.vy > 0, "Should bounce off top (vy becomes positive)"

    def test_bounce_off_bottom(self) -> None:
        g = _make_game()
        sc = Shuttlecock(x=150.0, y=234.0, vx=1.0, vy=5.0, color=0)
        g._update_shuttlecock(sc)
        assert sc.vy < 0, "Should bounce off bottom (vy becomes negative)"


# ------------------------------------------------------------------
# Test: Hit detection
# ------------------------------------------------------------------
class TestHitDetection:
    def test_hit_when_shuttlecock_close(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        g.player_racket_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g.shuttlecock = sc
        result = g._try_player_hit()
        assert result is True

    def test_no_hit_when_far_away(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        sc = Shuttlecock(x=float(PLAYER_X), y=200.0, vx=-1.0, vy=0.0, color=0)
        g.shuttlecock = sc
        result = g._try_player_hit()
        assert result is False

    def test_no_hit_on_ai_side(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        sc = Shuttlecock(x=200.0, y=100.0, vx=1.0, vy=0.0, color=0)
        g.shuttlecock = sc
        result = g._try_player_hit()
        assert result is False

    def test_no_hit_when_no_shuttlecock(self) -> None:
        g = _make_game()
        g.shuttlecock = None
        result = g._try_player_hit()
        assert result is False

    def test_no_hit_when_inactive(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0, active=False)
        g.shuttlecock = sc
        result = g._try_player_hit()
        assert result is False


# ------------------------------------------------------------------
# Test: Color matching and COMBO
# ------------------------------------------------------------------
class TestColorMatching:
    def test_match_racket_color_starts_combo(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        g.last_hit_color = -1
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.combo == 1
        assert g.last_hit_color == 0

    def test_same_color_consecutive_builds_combo(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        g.last_hit_color = 0
        g.combo = 1  # already hit once with same color
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.combo == 2

    def test_different_color_resets_combo(self) -> None:
        g = _make_game()
        g.player_racket_color = 1  # match shuttlecock color
        g.last_hit_color = 0
        g.combo = 3
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=1)
        g._on_player_hit(sc)
        assert g.combo == 1  # resets to 1 (new chain, racket matches but different last color)
        assert g.last_hit_color == 1

    def test_wrong_racket_color_gives_heat(self) -> None:
        g = _make_game()
        g.player_racket_color = 2
        g.combo = 1
        g.last_hit_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.combo == 0
        assert g.heat == HEAT_PER_WRONG_COLOR

    def test_score_increases_on_hit(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        old_score = g.score
        g._on_player_hit(sc)
        assert g.score > old_score

    def test_combo_bonus_increases_with_combo(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        g.last_hit_color = 0
        g.combo = 4
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        old_score = g.score
        g._on_player_hit(sc)
        # base 10 + combo 5 * 5 = 35
        assert g.score - old_score == 35

    def test_racket_color_advances_after_hit(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.player_racket_color == 1

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g.combo = 5
        g.max_combo = 3
        g.player_racket_color = 0
        g.last_hit_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.max_combo == 6


# ------------------------------------------------------------------
# Test: SUPER SMASH
# ------------------------------------------------------------------
class TestSuperSmash:
    def test_super_activates_at_threshold(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        g.last_hit_color = 0
        g.combo = COMBO_THRESHOLD - 1
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.combo >= COMBO_THRESHOLD
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_always_matches(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 100
        g.player_racket_color = 0
        g.combo = 5
        g.last_hit_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=1)  # different color
        g._on_player_hit(sc)
        assert g.combo == 6  # still increments in super mode
        assert g.heat == 0.0  # no heat in super mode

    def test_super_mode_triple_score(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 100
        g.player_racket_color = 0
        g.combo = 5
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        old_score = g.score
        g._on_player_hit(sc)
        # base 10 + combo 6 * 5 = 40, * 3 = 120
        assert g.score - old_score == 120

    def test_shake_on_super_activation(self) -> None:
        g = _make_game()
        g.combo = COMBO_THRESHOLD - 1
        g.player_racket_color = 0
        g.last_hit_color = 0
        g.shake_frames = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.shake_frames > 0


# ------------------------------------------------------------------
# Test: HEAT system
# ------------------------------------------------------------------
class TestHeatSystem:
    def test_heat_decays_over_time(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_never_negative(self) -> None:
        g = _make_game()
        g.heat = 0.0
        for _ in range(10):
            g._update_heat()
        assert g.heat >= 0.0

    def test_heat_decay_rate(self) -> None:
        g = _make_game()
        g.heat = 20.0
        g._update_heat()
        assert g.heat == 20.0 - HEAT_DECAY

    def test_miss_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 10.0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g.shuttlecock = sc
        g._trail_record = [(100.0, 100.0)]
        g._on_player_miss()
        assert g.heat == 10.0 + HEAT_PER_MISS

    def test_wrong_color_adds_heat(self) -> None:
        g = _make_game()
        g.player_racket_color = 2
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert g.heat == HEAT_PER_WRONG_COLOR

    def test_miss_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 5
        g.last_hit_color = 2
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g.shuttlecock = sc
        g._trail_record = [(100.0, 100.0)]
        g._on_player_miss()
        assert g.combo == 0
        assert g.last_hit_color == -1


# ------------------------------------------------------------------
# Test: Ghost trail
# ------------------------------------------------------------------
class TestGhostTrail:
    def test_miss_creates_ghost_trail(self) -> None:
        g = _make_game()
        g._trail_record = [(100.0, 100.0), (110.0, 105.0), (120.0, 110.0), (130.0, 115.0), (140.0, 120.0)]
        g.shuttlecock = Shuttlecock(x=150.0, y=100.0, vx=-1.0, vy=0.0, color=0)
        old_count = len(g.ghost_trail)
        g._on_player_miss()
        assert len(g.ghost_trail) > old_count

    def test_ghost_bonus_collected(self) -> None:
        g = _make_game()
        g._ghost_bonus_collected = False
        g.ghost_trail = [GhostTrail(x=100.0, y=100.0, life=60, color=8)]
        sc = Shuttlecock(x=100.0, y=100.0, vx=2.0, vy=0.0, color=0)
        g.shuttlecock = sc
        old_score = g.score
        g._check_ghost_bonus()
        assert g.score == old_score + 25
        assert g._ghost_bonus_collected is True

    def test_ghost_bonus_not_collected_when_far(self) -> None:
        g = _make_game()
        g._ghost_bonus_collected = False
        g.ghost_trail = [GhostTrail(x=100.0, y=100.0, life=60, color=8)]
        sc = Shuttlecock(x=200.0, y=200.0, vx=2.0, vy=0.0, color=0)
        g.shuttlecock = sc
        old_score = g.score
        g._check_ghost_bonus()
        assert g.score == old_score
        assert g._ghost_bonus_collected is False

    def test_ghost_trail_updates(self) -> None:
        g = _make_game()
        g.ghost_trail = [
            GhostTrail(x=100.0, y=100.0, life=5, color=8),
            GhostTrail(x=110.0, y=110.0, life=0, color=3),
        ]
        g._update_ghost_trail()
        assert len(g.ghost_trail) == 1
        assert g.ghost_trail[0].life == 4


# ------------------------------------------------------------------
# Test: Scoring
# ------------------------------------------------------------------
class TestScoring:
    def test_base_score_on_hit(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        # combo=1, base=10 + 1*5 = 15
        assert g.score == 15

    def test_higher_combo_gives_more_score(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        g.last_hit_color = 0
        g.combo = 3
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        old_score = g.score
        g._on_player_hit(sc)
        # combo=4, base=10 + 4*5 = 30
        assert g.score - old_score == 30


# ------------------------------------------------------------------
# Test: AI
# ------------------------------------------------------------------
class TestAI:
    def test_ai_moves_toward_shuttlecock(self) -> None:
        g = _make_game()
        g.ai_y = 100.0
        sc = Shuttlecock(x=200.0, y=150.0, vx=1.0, vy=0.0, color=0)
        g.shuttlecock = sc
        old_y = g.ai_y
        g._update_ai()
        assert g.ai_y != old_y

    def test_ai_returns_shuttlecock(self) -> None:
        g = _make_game()
        g.ai_y = 100.0
        sc = Shuttlecock(x=float(AI_X), y=100.0, vx=1.0, vy=0.0, color=0)
        old_vx = sc.vx
        g._ai_return(sc)
        assert sc.vx < 0  # returns toward player
        assert sc.vx != old_vx


# ------------------------------------------------------------------
# Test: Serve
# ------------------------------------------------------------------
class TestServe:
    def test_serve_creates_shuttlecock(self) -> None:
        g = _make_game()
        g.shuttlecock = None
        g._serve_shuttlecock()
        assert g.shuttlecock is not None
        assert g.shuttlecock.active is True
        assert g.shuttlecock.vx < 0  # moves toward player

    def test_serve_resets_ghost_bonus(self) -> None:
        g = _make_game()
        g._ghost_bonus_collected = True
        g._serve_shuttlecock()
        assert g._ghost_bonus_collected is False

    def test_serve_clears_trail_record(self) -> None:
        g = _make_game()
        g._trail_record = [(100.0, 100.0)]
        g._serve_shuttlecock()
        assert len(g._trail_record) == 0


# ------------------------------------------------------------------
# Test: Hit shuttlecock direction
# ------------------------------------------------------------------
class TestHitDirection:
    def test_player_hit_launches_toward_ai(self) -> None:
        g = _make_game()
        g.player_racket_color = 0
        sc = Shuttlecock(x=float(PLAYER_X + 5), y=100.0, vx=-1.0, vy=0.0, color=0)
        g._on_player_hit(sc)
        assert sc.vx > 0  # toward AI

    def test_ai_return_launches_toward_player(self) -> None:
        g = _make_game()
        g.ai_y = 100.0
        sc = Shuttlecock(x=float(AI_X), y=100.0, vx=1.0, vy=0.0, color=0)
        g._ai_return(sc)
        assert sc.vx < 0  # toward player


# ------------------------------------------------------------------
# Test: Reset
# ------------------------------------------------------------------
class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 10
        g.heat = 80.0
        g.super_mode = True
        g.super_timer = 50
        g.shuttlecock = Shuttlecock(x=100.0, y=100.0, vx=1.0, vy=0.0, color=0)
        g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=7)]
        g.floating_texts = [FloatingText(x=0, y=0, text="test", life=1, color=7)]
        g.ghost_trail = [GhostTrail(x=0, y=0, life=1, color=7)]
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.super_mode is False
        assert g.super_timer == 0
        assert g.shuttlecock is None
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert len(g.ghost_trail) == 0
        assert g.last_hit_color == -1
        assert g.phase == Phase.TITLE


# ------------------------------------------------------------------
# Test: Particle system
# ------------------------------------------------------------------
class TestParticles:
    def test_spawn_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 10)
        assert len(g.particles) == 10

    def test_update_particles_reduces_life(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 3)
        for p in g.particles:
            p.life = 1
        g._update_particles()
        assert len(g.particles) == 0

    def test_update_particles_moves(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 1)
        px_before = g.particles[0].x
        py_before = g.particles[0].y
        g._update_particles()
        assert g.particles[0].x != px_before or g.particles[0].y != py_before


# ------------------------------------------------------------------
# Test: Floating text
# ------------------------------------------------------------------
class TestFloatingText:
    def test_add_floating_text(self) -> None:
        g = _make_game()
        g._add_floating_text(100.0, 100.0, "test", 7)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "test"

    def test_floating_text_fades(self) -> None:
        g = _make_game()
        g._add_floating_text(100.0, 100.0, "test", 7, life=1)
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_floating_text_rises(self) -> None:
        g = _make_game()
        g._add_floating_text(100.0, 100.0, "test", 7, life=10)
        y_before = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < y_before


# ------------------------------------------------------------------
# Test: dist_player_to_shuttlecock
# ------------------------------------------------------------------
class TestDistance:
    def test_distance_close(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        sc = Shuttlecock(x=float(PLAYER_X), y=100.0, vx=0.0, vy=0.0, color=0)
        d = g._dist_player_to_shuttlecock(sc)
        # racket center is at (PLAYER_X + RACKET_W/2, 100 + RACKET_H/2)
        # shuttlecock at (PLAYER_X, 100)
        expected = abs(RACKET_H / 2)
        assert math.isclose(d, expected, rel_tol=0.1)

    def test_distance_far(self) -> None:
        g = _make_game()
        g.player_y = 100.0
        sc = Shuttlecock(x=200.0, y=200.0, vx=0.0, vy=0.0, color=0)
        d = g._dist_player_to_shuttlecock(sc)
        assert d > RACKET_H
