"""Headless logic tests for CHRONO CHAIN."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/276_chrono_chain")
from main import (
    Game,
    Phase,
    Crystal,
    PathPoint,
    Particle,
    FloatingText,
    GAME_TIME,
    SUPER_DURATION,
    MAX_HEAT,
    HEAT_MISMATCH,
    COMBO_FOR_SUPER,
    RECORD_INTERVAL,
    MAX_CRYSTALS,
    CRYSTAL_COLORS,
    COLOR_RED,
    COLOR_LIME,
    COLOR_DARK_BLUE,
    COLOR_YELLOW,
    COLOR_WHITE,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.PLAYING
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_TIME
    g.super_timer = 0
    g.frame = 0
    g.player_x = 160.0
    g.player_y = 120.0
    g.last_color = None
    g.crystals = []
    g.path = []
    g.echo_path = []
    g.echo_idx = 0
    g.echo_active = False
    g.echo_x = 0.0
    g.echo_y = 0.0
    g.record_timer = RECORD_INTERVAL
    g.shake_frames = 0
    g.particles = []
    g.floating_texts = []
    g.spawn_timer = 60
    g.spawn_interval = 60
    g.crystal_lifetime = 240
    g._rng = random.Random(42)
    return g


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_crystal(self):
        c = Crystal(x=100.0, y=120.0, color=COLOR_RED)
        assert c.x == 100.0
        assert c.y == 120.0
        assert c.color == COLOR_RED
        assert c.alive is True

    def test_path_point(self):
        pp = PathPoint(x=50.0, y=60.0, frame=30)
        assert pp.x == 50.0
        assert pp.y == 60.0
        assert pp.frame == 30

    def test_particle(self):
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, color=COLOR_RED, life=20)
        assert p.life == 20
        assert p.color == COLOR_RED

    def test_floating_text(self):
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=COLOR_WHITE, life=30)
        assert ft.text == "+10"
        assert ft.life == 30


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_crystal_colors(self):
        assert len(CRYSTAL_COLORS) == 4
        assert CRYSTAL_COLORS == (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)

    def test_combo_for_super(self):
        assert COMBO_FOR_SUPER == 4

    def test_super_duration(self):
        assert SUPER_DURATION == 300

    def test_game_time(self):
        assert GAME_TIME == 1800

    def test_heat_max(self):
        assert MAX_HEAT == 100.0

    def test_heat_mismatch(self):
        assert HEAT_MISMATCH == 15.0

    def test_max_crystals(self):
        assert MAX_CRYSTALS == 12


# ═══════════════════════════════════════════════════════════════
# Crystal collection
# ═══════════════════════════════════════════════════════════════


class TestCrystalCollection:
    def test_first_collection_sets_last_color(self):
        g = _make_game()
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert not c.alive
        assert g.last_color == COLOR_RED
        assert g.combo == 1
        assert g.score > 0

    def test_same_color_builds_combo(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 2
        g.score = 0
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.combo == 3
        assert g.score > 0

    def test_wrong_color_resets_combo_adds_heat(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 3
        g.heat = 0.0
        c = Crystal(x=160.0, y=120.0, color=COLOR_LIME)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.combo == 0
        assert g.last_color == COLOR_LIME
        assert g.heat == HEAT_MISMATCH
        assert g.shake_frames == 8

    def test_combo_4_triggers_super(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 3
        g.super_timer = 0
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.combo == 4
        assert g.super_timer == SUPER_DURATION
        assert g.shake_frames == 6

    def test_super_mode_any_color_match(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 4
        g.super_timer = 100
        c = Crystal(x=160.0, y=120.0, color=COLOR_LIME)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.combo == 5  # combo continues
        assert g.heat == 0.0  # no heat added

    def test_super_3x_score(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 4
        g.super_timer = 100
        g.score = 0
        c = Crystal(x=160.0, y=120.0, color=COLOR_LIME)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        # combo 5, 10 * 5 * 3 = 150
        assert g.score == 150

    def test_echo_collect_affects_combo(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 2
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=True)
        assert g.combo == 3
        assert g.score > 0

    def test_already_dead_crystal_ignored(self):
        g = _make_game()
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED, alive=False)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.combo == 0

    def test_max_combo_tracking(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 2
        g.max_combo = 2
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.max_combo == 3


# ═══════════════════════════════════════════════════════════════
# Player movement
# ═══════════════════════════════════════════════════════════════


class TestMovement:
    def test_move_left(self):
        g = _make_game()
        g.player_x = 100.0
        g._move_player(-1.0, 0.0)
        assert g.player_x < 100.0

    def test_move_right(self):
        g = _make_game()
        g.player_x = 100.0
        g._move_player(1.0, 0.0)
        assert g.player_x > 100.0

    def test_clamp_left_boundary(self):
        g = _make_game()
        g.player_x = 60.0
        g._move_player(-1.0, 0.0)
        from main import PLAYFIELD_X, PLAYER_R
        assert g.player_x >= PLAYFIELD_X + PLAYER_R

    def test_clamp_right_boundary(self):
        g = _make_game()
        from main import PLAYFIELD_X, COLS, CELL, PLAYER_R
        right = PLAYFIELD_X + COLS * CELL - PLAYER_R
        g.player_x = right
        g._move_player(1.0, 0.0)
        assert g.player_x <= PLAYFIELD_X + COLS * CELL - PLAYER_R

    def test_diagonal_normalized(self):
        g = _make_game()
        g.player_x = 100.0
        g.player_y = 100.0
        g._move_player(1.0, 1.0)
        dx = g.player_x - 100.0
        dy = g.player_y - 100.0
        assert abs(dx - dy) < 0.01


# ═══════════════════════════════════════════════════════════════
# Heat system
# ═══════════════════════════════════════════════════════════════


class TestHeat:
    def test_heat_net_change(self):
        g = _make_game()
        g.heat = 10.0
        # passive gain (0.03) > decay (0.02), net +0.01 per frame
        g._update_heat()
        assert 10.0 < g.heat < 10.02

    def test_heat_floor_zero(self):
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat >= 0.0

    def test_heat_passive_increase(self):
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        # HEAT_PER_FRAME = 0.03, HEAT_DECAY = 0.02 → net +0.01
        assert g.heat > 0.0

    def test_mismatch_adds_heat(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.heat = 0.0
        c = Crystal(x=160.0, y=120.0, color=COLOR_LIME)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert g.heat == HEAT_MISMATCH

    def test_heat_at_max_game_over(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = MAX_HEAT
        g.score = 100
        g.best_score = 50
        g._end_game()
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 100


# ═══════════════════════════════════════════════════════════════
# Timer
# ═══════════════════════════════════════════════════════════════


class TestTimer:
    def test_timer_counts_down(self):
        g = _make_game()
        g.timer = 100
        g._update_timer()
        assert g.timer == 99

    def test_timer_floor_zero(self):
        g = _make_game()
        g.timer = 0
        g._update_timer()
        assert g.timer == 0


# ═══════════════════════════════════════════════════════════════
# Phase and reset
# ═══════════════════════════════════════════════════════════════


class TestPhases:
    def test_reset_sets_title(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.reset()
        assert g.phase == Phase.TITLE

    def test_reset_clears_score(self):
        g = _make_game()
        g.score = 999
        g.reset()
        assert g.score == 0

    def test_reset_clears_combo(self):
        g = _make_game()
        g.combo = 5
        g.reset()
        assert g.combo == 0

    def test_reset_clears_heat(self):
        g = _make_game()
        g.heat = 80.0
        g.reset()
        assert g.heat == 0.0

    def test_reset_clears_crystals(self):
        g = _make_game()
        g.crystals = [Crystal(100, 100, COLOR_RED)]
        g.reset()
        assert len(g.crystals) == 0

    def test_reset_clears_particles_and_texts(self):
        g = _make_game()
        g.particles = [Particle(0, 0, 0, 0, COLOR_RED, 1)]
        g.floating_texts = [FloatingText(0, 0, "test", COLOR_WHITE, 1)]
        g.reset()
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_best_score_preserved(self):
        g = _make_game()
        g.best_score = 500
        g.reset()
        assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


class TestParticles:
    def test_spawn_collect_particles_normal(self):
        g = _make_game()
        g._spawn_collect_particles(100.0, 100.0, COLOR_RED, big=False)
        assert len(g.particles) == 8

    def test_spawn_collect_particles_big(self):
        g = _make_game()
        g._spawn_collect_particles(100.0, 100.0, COLOR_RED, big=True)
        assert len(g.particles) == 16

    def test_particle_life_decreases(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=COLOR_RED, life=10)
        g.particles = [p]
        g._update_particles()
        assert p.life == 9

    def test_particle_gravity(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=COLOR_RED, life=10)
        g.particles = [p]
        g._update_particles()
        assert p.vy == 0.1  # gravity applied to vy
        # y doesn't move on first frame because vy was 0 before update
        g._update_particles()
        assert p.y > 100.0  # moves on second frame
        assert p.vy > 0.1

    def test_dead_particles_removed(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=COLOR_RED, life=1)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0

    def test_super_activates_particles(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 120.0
        g._activate_super()
        assert len(g.particles) == 20


# ═══════════════════════════════════════════════════════════════
# Floating texts
# ═══════════════════════════════════════════════════════════════


class TestFloatingTexts:
    def test_spawn_float(self):
        g = _make_game()
        g._spawn_float(100.0, 50.0, "+10", COLOR_WHITE)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "+10"
        assert g.floating_texts[0].life == 30

    def test_float_rises(self):
        g = _make_game()
        g._spawn_float(100.0, 50.0, "+10", COLOR_WHITE)
        g._update_floating_texts()
        assert g.floating_texts[0].y == 49.5
        assert g.floating_texts[0].life == 29

    def test_dead_floats_removed(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=COLOR_WHITE, life=1)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════
# Echo system
# ═══════════════════════════════════════════════════════════════


class TestEcho:
    def test_echo_inactive_by_default(self):
        g = _make_game()
        assert g.echo_active is False
        assert len(g.echo_path) == 0

    def test_record_path_adds_point(self):
        g = _make_game()
        g.record_timer = 10
        assert len(g.path) == 0
        g._record_path()
        assert len(g.path) == 1

    def test_record_interval_transfers_to_echo(self):
        g = _make_game()
        g.record_timer = 1
        g.player_x = 140.0
        g.player_y = 100.0
        for _ in range(15):
            g.path.append(PathPoint(x=g.player_x, y=g.player_y, frame=g.frame))
        g._record_path()
        # record_timer expires, path transfers to echo_path and path clears
        assert len(g.echo_path) == 16
        if g.echo_active:
            assert len(g.echo_path) > 0

    def test_echo_collects_crystal(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 1
        g.echo_active = True
        g.echo_x = 160.0
        g.echo_y = 120.0
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g.echo_path = [PathPoint(x=160.0, y=120.0, frame=0)]
        g.echo_idx = 0
        g._update_echo()
        assert not c.alive
        assert g.combo == 2

    def test_echo_reaches_end_deactivates(self):
        g = _make_game()
        g.echo_active = True
        g.echo_path = [PathPoint(x=160.0, y=120.0, frame=0)]
        g.echo_idx = 1
        g._update_echo()
        assert g.echo_active is False


# ═══════════════════════════════════════════════════════════════
# Crystal spawning
# ═══════════════════════════════════════════════════════════════


class TestSpawning:
    def test_spawn_crystals_fills_upto_max(self):
        g = _make_game()
        g.spawn_timer = 1
        g.crystals = []
        g._spawn_crystals()
        # Should spawn up to MAX_CRYSTALS if timer triggers
        assert len(g.crystals) <= MAX_CRYSTALS

    def test_no_spawn_at_max(self):
        g = _make_game()
        g.spawn_timer = 1
        g.crystals = [Crystal(i * 20 + 60, 60, COLOR_RED) for i in range(MAX_CRYSTALS)]
        g._spawn_crystals()
        assert len(g.crystals) == MAX_CRYSTALS

    def test_spawned_crystals_on_playfield(self):
        g = _make_game()
        g.spawn_timer = 1
        g.crystals = []
        g._spawn_crystals()
        from main import PLAYFIELD_X, PLAYFIELD_Y, COLS, CELL
        for c in g.crystals:
            assert PLAYFIELD_X < c.x < PLAYFIELD_X + COLS * CELL
            assert PLAYFIELD_Y < c.y < PLAYFIELD_Y + 8 * CELL


# ═══════════════════════════════════════════════════════════════
# SUPER CHRONO
# ═══════════════════════════════════════════════════════════════


class TestSuper:
    def test_activate_super_sets_timer(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 120.0
        g._activate_super()
        assert g.super_timer == SUPER_DURATION
        assert g.shake_frames == 6

    def test_super_floating_text(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 120.0
        g._activate_super()
        assert any("SUPER" in ft.text for ft in g.floating_texts)

    def test_super_spawns_20_particles(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 120.0
        g._activate_super()
        assert len(g.particles) == 20


# ═══════════════════════════════════════════════════════════════
# Score and best score
# ═══════════════════════════════════════════════════════════════


class TestScore:
    def test_collect_gives_score(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 2
        g.score = 0
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        # combo becomes 3, score = 10 * 3 = 30
        assert g.score == 30

    def test_best_score_updates(self):
        g = _make_game()
        g.score = 700
        g.best_score = 500
        g._end_game()
        assert g.best_score == 700

    def test_best_score_not_lowered(self):
        g = _make_game()
        g.best_score = 500
        g.score = 300
        g._end_game()
        assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
# Float text content
# ═══════════════════════════════════════════════════════════════


class TestFloatContent:
    def test_collect_spawns_score_float(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 1
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        # combo becomes 2, triggers both score float and COMBO x2 float
        assert len(g.floating_texts) == 2
        assert any("+" in ft.text for ft in g.floating_texts)
        assert any("COMBO" in ft.text for ft in g.floating_texts)

    def test_mismatch_spawns_wrong_float(self):
        g = _make_game()
        g.last_color = COLOR_RED
        c = Crystal(x=160.0, y=120.0, color=COLOR_LIME)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        assert any("WRONG" in ft.text for ft in g.floating_texts)

    def test_combo_milestone_float(self):
        g = _make_game()
        g.last_color = COLOR_RED
        g.combo = 1
        c = Crystal(x=160.0, y=120.0, color=COLOR_RED)
        g.crystals = [c]
        g._collect_crystal(c, is_echo=False)
        texts = [ft.text for ft in g.floating_texts]
        assert any("COMBO" in t for t in texts)
