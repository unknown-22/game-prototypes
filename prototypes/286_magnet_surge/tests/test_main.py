from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    BASE_SCORE,
    COMBO_FOR_SUPER,
    GAME_TIME,
    HEAT_MISMATCH,
    HEAT_MAX,
    PARTICLE_COUNT,
    SCRAP_COLORS,
    SUPER_DURATION,
    Game,
    Particle,
    Phase,
    Scrap,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.timer = GAME_TIME
    g.best_score = 0
    g.polarity = True
    g.last_color = -1
    g.scraps = []
    g.particles = []
    g.floating_texts = []
    g.spawn_timer = 0
    g.mouse_x = SCREEN_W // 2
    g.mouse_y = SCREEN_H // 2
    g.rainbow_tick = 0
    g._elapsed_frames = 0
    g.font = None
    return g


SCREEN_W = 320
SCREEN_H = 240


# --------------------------------------------------------------------------
# Scrap
# --------------------------------------------------------------------------
class TestScrapBounce:
    def test_bounce_left_edge(self) -> None:
        g = _make_game()
        scrap = Scrap(x=-5.0, y=120.0, vx=-2.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._update_scraps()
        assert scrap.x >= 0
        assert scrap.vx > 0

    def test_bounce_right_edge(self) -> None:
        g = _make_game()
        scrap = Scrap(x=SCREEN_W + 5.0, y=120.0, vx=2.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._update_scraps()
        assert scrap.x <= SCREEN_W
        assert scrap.vx < 0

    def test_bounce_top_edge(self) -> None:
        g = _make_game()
        scrap = Scrap(x=160.0, y=-5.0, vx=0.0, vy=-2.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._update_scraps()
        assert scrap.y >= 0
        assert scrap.vy > 0

    def test_bounce_bottom_edge(self) -> None:
        g = _make_game()
        scrap = Scrap(x=160.0, y=SCREEN_H + 5.0, vx=0.0, vy=2.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._update_scraps()
        assert scrap.y <= SCREEN_H
        assert scrap.vy < 0


# --------------------------------------------------------------------------
# Magnet force
# --------------------------------------------------------------------------
class TestMagnetForce:
    def test_attract_pulls_scrap_toward_magnet(self) -> None:
        g = _make_game()
        g.polarity = True
        g.mouse_x = 100
        g.mouse_y = 100
        scrap = Scrap(x=105.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._apply_magnet_force(scrap)
        assert scrap.vx < 0

    def test_repel_pushes_scrap_away(self) -> None:
        g = _make_game()
        g.polarity = False
        g.mouse_x = 100
        g.mouse_y = 100
        scrap = Scrap(x=105.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._apply_magnet_force(scrap)
        assert scrap.vx > 0

    def test_no_force_outside_radius(self) -> None:
        g = _make_game()
        g.polarity = True
        g.mouse_x = 100
        g.mouse_y = 100
        scrap = Scrap(x=300.0, y=300.0, vx=1.0, vy=1.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._apply_magnet_force(scrap)
        assert scrap.vx == 1.0
        assert scrap.vy == 1.0

    def test_super_always_attracts(self) -> None:
        g = _make_game()
        g.polarity = False
        g.super_timer = 100
        g.mouse_x = 100
        g.mouse_y = 100
        scrap = Scrap(x=105.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._apply_magnet_force(scrap)
        assert scrap.vx < 0

    def test_super_has_larger_radius(self) -> None:
        g = _make_game()
        g.polarity = True
        g.super_timer = 100
        g.mouse_x = 100
        g.mouse_y = 100
        scrap = Scrap(x=120.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._apply_magnet_force(scrap)
        assert scrap.vx < 0


# --------------------------------------------------------------------------
# Damping
# --------------------------------------------------------------------------
class TestDamping:
    def test_damping_reduces_velocity(self) -> None:
        g = _make_game()
        scrap = Scrap(x=160.0, y=120.0, vx=10.0, vy=10.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._update_scraps()
        assert abs(scrap.vx) < 10.0
        assert abs(scrap.vy) < 10.0


# --------------------------------------------------------------------------
# Collection
# --------------------------------------------------------------------------
class TestCollection:
    def test_first_scrap_always_matches(self) -> None:
        g = _make_game()
        g.last_color = -1
        g.combo = 0
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.combo == 1
        assert g.score == BASE_SCORE * 1
        assert len(g.scraps) == 0

    def test_same_color_builds_combo(self) -> None:
        g = _make_game()
        g.last_color = SCRAP_COLORS[0]
        g.combo = 2
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.combo == 3
        assert g.score == BASE_SCORE * 3

    def test_wrong_color_resets_combo_and_adds_heat(self) -> None:
        g = _make_game()
        g.last_color = SCRAP_COLORS[0]
        g.combo = 3
        g.heat = 10.0
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[1], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.combo == 0
        assert g.heat == 10.0 + HEAT_MISMATCH

    def test_super_mode_always_matches(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.last_color = SCRAP_COLORS[0]
        g.combo = 1
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[1], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.combo == 2
        assert g.score > 0

    def test_not_near_enough_no_collection(self) -> None:
        g = _make_game()
        scrap = Scrap(x=200.0, y=200.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert len(g.scraps) == 1


# --------------------------------------------------------------------------
# Super Magnet
# --------------------------------------------------------------------------
class TestSuperMagnet:
    def test_combo_4_activates_super(self) -> None:
        g = _make_game()
        g.combo = 3
        g.last_color = SCRAP_COLORS[0]
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.super_timer == SUPER_DURATION
        assert g.combo >= COMBO_FOR_SUPER

    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_timer = 10
        g.update()
        assert g.super_timer == 9

    def test_super_deactivates(self) -> None:
        g = _make_game()
        g.super_timer = 1
        g.update()
        assert g.super_timer == 0
        assert not g.is_super


# --------------------------------------------------------------------------
# Heat
# --------------------------------------------------------------------------
class TestHeat:
    def test_heat_decays_over_time(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_does_not_go_below_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_100_triggers_game_over(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._end_game(overheat=True)
        assert g.phase == Phase.GAME_OVER

    def test_mismatch_adds_heat(self) -> None:
        g = _make_game()
        g.last_color = SCRAP_COLORS[0]
        g.heat = 20.0
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[1], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.heat == 20.0 + HEAT_MISMATCH


# --------------------------------------------------------------------------
# Scrap spawning
# --------------------------------------------------------------------------
class TestScrapSpawning:
    def test_spawn_adds_scrap(self) -> None:
        g = _make_game()
        g.timer = GAME_TIME
        assert len(g.scraps) == 0
        g._spawn_scrap()
        assert len(g.scraps) == 1

    def test_spawn_respects_max(self) -> None:
        g = _make_game()
        for _ in range(20):
            g._spawn_scrap()
        assert len(g.scraps) <= 12

    def test_spawn_assigns_valid_color(self) -> None:
        g = _make_game()
        g._spawn_scrap()
        assert g.scraps[0].color in SCRAP_COLORS


# --------------------------------------------------------------------------
# Scrap expiry
# --------------------------------------------------------------------------
class TestScrapExpiry:
    def test_expired_scrap_removed(self) -> None:
        g = _make_game()
        g.spawn_timer = 9999
        g.scraps.append(Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=0))
        g.update()
        assert len(g.scraps) == 0

    def test_alive_scrap_kept(self) -> None:
        g = _make_game()
        g.spawn_timer = 9999
        g.scraps.append(Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=10))
        g.update()
        assert len(g.scraps) == 1


# --------------------------------------------------------------------------
# Particles
# --------------------------------------------------------------------------
class TestParticles:
    def test_spawn_particles_on_collect(self) -> None:
        g = _make_game()
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert len(g.particles) == PARTICLE_COUNT

    def test_particles_life_decrements(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=5))
        g._update_particles()
        assert g.particles[0].life == 4

    def test_dead_particles_removed(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=1))
        g._update_particles()
        assert len(g.particles) == 0


# --------------------------------------------------------------------------
# Floating Text
# --------------------------------------------------------------------------
class TestFloatingText:
    def test_spawn_floating_text(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "TEST"

    def test_floating_text_moves_up(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        initial_y = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < initial_y

    def test_floating_text_expires(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        g.floating_texts[0].life = 1
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# --------------------------------------------------------------------------
# Timer
# --------------------------------------------------------------------------
class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        initial = g.timer
        g.update()
        assert g.timer == initial - 1

    def test_timer_zero_triggers_game_over(self) -> None:
        g = _make_game()
        g.timer = 1
        g.update()
        assert g.phase == Phase.GAME_OVER


# --------------------------------------------------------------------------
# Reset
# --------------------------------------------------------------------------
class TestReset:
    def test_reset_clears_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 5
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.phase == Phase.PLAYING

    def test_reset_clears_scraps(self) -> None:
        g = _make_game()
        g.scraps.append(Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100))
        g.reset()
        assert len(g.scraps) == 0

    def test_best_score_preserved(self) -> None:
        g = _make_game()
        g.best_score = 1000
        g.reset()
        assert g.best_score == 1000


# --------------------------------------------------------------------------
# Score calculation
# --------------------------------------------------------------------------
class TestScoreCalculation:
    def test_combo_multiplies_score(self) -> None:
        g = _make_game()
        g.last_color = SCRAP_COLORS[0]
        g.combo = 4
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.score == BASE_SCORE * 5

    def test_super_magnet_3x_multiplier(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.last_color = SCRAP_COLORS[0]
        g.combo = 1
        scrap = Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g.mouse_x = 100
        g.mouse_y = 100
        g._check_collection()
        assert g.score == BASE_SCORE * 2 * 3


# --------------------------------------------------------------------------
# Max combo
# --------------------------------------------------------------------------
class TestMaxCombo:
    def test_max_combo_updated(self) -> None:
        g = _make_game()
        g.last_color = SCRAP_COLORS[0]
        for i in range(3):
            g.scraps.append(Scrap(x=100.0, y=100.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100))
            g.mouse_x = 100
            g.mouse_y = 100
            g._check_collection()
        assert g.max_combo == 3


# --------------------------------------------------------------------------
# Difficulty progression
# --------------------------------------------------------------------------
class TestDifficultyProgression:
    def test_progress_zero_at_start(self) -> None:
        g = _make_game()
        g.timer = GAME_TIME
        assert g._progress() == 0.0

    def test_progress_one_at_end(self) -> None:
        g = _make_game()
        g.timer = 0
        assert g._progress() == 1.0

    def test_spawn_interval_decreases_over_time(self) -> None:
        g = _make_game()
        g.timer = GAME_TIME
        early = g._spawn_interval()
        g.timer = 1
        late = g._spawn_interval()
        assert late <= early


# --------------------------------------------------------------------------
# Polarity toggle
# --------------------------------------------------------------------------
class TestPolarityToggle:
    def test_toggle_flips_polarity(self) -> None:
        g = _make_game()
        g.polarity = True
        g.polarity = not g.polarity
        assert not g.polarity

    def test_repel_does_not_attract(self) -> None:
        g = _make_game()
        g.polarity = False
        g.mouse_x = 200
        g.mouse_y = 200
        scrap = Scrap(x=205.0, y=200.0, vx=0.0, vy=0.0, color=SCRAP_COLORS[0], life=100)
        g.scraps.append(scrap)
        g._apply_magnet_force(scrap)
        assert scrap.vx > 0
