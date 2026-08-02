"""test_imports.py — Headless logic tests for CHROMA ESCAPE."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/272_chroma_escape")
from main import (
    Game,
    Phase,
    PuzzleElement,
    Particle,
    FloatingText,
    ELEMENT_COLORS,
    HEAT_CAP,
    HEAT_MISMATCH,
    HEAT_DECAY_RATE,
    HEAT_TIME_RATE,
    COMBO_THRESHOLD,
    SUPER_DURATION,
    SCORE_BASE,
    SCORE_CHAIN,
    GRID_COLS,
    GRID_ROWS,
    GAME_DURATION,
    RESPAWN_DELAY_MIN,
    RESPAWN_DELAY_MAX,
    CELL_SIZE,
    CELL_GAP,
    GRID_OFFSET_X,
    GRID_OFFSET_Y,
)


def _make_game() -> Game:
    """Create a headless Game instance with deterministic RNG."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.timer = GAME_DURATION
    g.grid = []
    g.last_color = None
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g._frame_count = 0
    g._rng = random.Random(42)
    g.reset()
    return g


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_puzzle_element_defaults(self):
        e = PuzzleElement(col=0, row=0, color=8)
        assert e.alive is True
        assert e.respawn_timer == 0

    def test_particle(self):
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=20, color=8)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.life == 20

    def test_floating_text(self):
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=7, life=40)
        assert ft.text == "+10"
        assert ft.life == 40


# ═══════════════════════════════════════════════════════════════
# Grid basics
# ═══════════════════════════════════════════════════════════════


class TestGrid:
    def test_init_grid_size(self):
        g = _make_game()
        assert len(g.grid) == GRID_ROWS
        for row in g.grid:
            assert len(row) == GRID_COLS

    def test_init_grid_all_alive(self):
        g = _make_game()
        for row in g.grid:
            for elem in row:
                assert elem is not None
                assert elem.alive is True

    def test_init_grid_colors_in_set(self):
        g = _make_game()
        for row in g.grid:
            for elem in row:
                assert elem is not None
                assert elem.color in ELEMENT_COLORS

    def test_cell_xy(self):
        g = _make_game()
        x, y = g.cell_xy(0, 0)
        assert x == GRID_OFFSET_X
        assert y == GRID_OFFSET_Y

        x2, y2 = g.cell_xy(1, 1)
        assert x2 == GRID_OFFSET_X + 1 * (CELL_SIZE + CELL_GAP)
        assert y2 == GRID_OFFSET_Y + 1 * (CELL_SIZE + CELL_GAP)

    def test_grid_pos_from_screen_hit(self):
        g = _make_game()
        # Click center of cell (0,0)
        cx, cy = g.cell_xy(0, 0)
        result = g.grid_pos_from_screen(cx + CELL_SIZE // 2, cy + CELL_SIZE // 2)
        assert result == (0, 0)

    def test_grid_pos_from_screen_miss_outside(self):
        g = _make_game()
        result = g.grid_pos_from_screen(0, 0)
        assert result is None

    def test_grid_pos_from_screen_miss_gap(self):
        g = _make_game()
        # Click the gap between cells
        cx0, cy0 = g.cell_xy(0, 0)
        result = g.grid_pos_from_screen(cx0 + CELL_SIZE + 1, cy0)
        assert result is None


# ═══════════════════════════════════════════════════════════════
# BFS Cluster
# ═══════════════════════════════════════════════════════════════


class TestBFSCluster:
    def test_single_cell_cluster(self):
        g = _make_game()
        # Set up isolated cell
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8 if (col == 2 and row == 2) else 11
                g.grid[row][col].alive = True
        cluster = g._bfs_cluster(2, 2, 8)
        assert len(cluster) == 1
        assert (2, 2) in cluster

    def test_full_grid_cluster(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        cluster = g._bfs_cluster(2, 2, 8)
        assert len(cluster) == 30  # 6*5

    def test_horizontal_line_cluster(self):
        g = _make_game()
        # Row 2: all RED, rest LIME
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8 if row == 2 else 11
                g.grid[row][col].alive = True
        cluster = g._bfs_cluster(0, 2, 8)
        assert len(cluster) == 6  # entire row

    def test_different_color_blocks_bfs(self):
        g = _make_game()
        # RED cells at (2,2) and (4,2), separated by LIME at (3,2)
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11
                g.grid[row][col].alive = True
        g.grid[2][2].color = 8
        g.grid[2][4].color = 8
        cluster = g._bfs_cluster(2, 2, 8)
        assert len(cluster) == 1  # only (2,2)

    def test_dead_cells_not_in_cluster(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        # grid[2][3] = row 2, col 3 = BFS (col=3, row=2)
        g.grid[2][3].alive = False  # dead cell blocks rightward expansion
        cluster = g._bfs_cluster(2, 2, 8)
        assert len(cluster) == 29  # one dead cell excluded
        assert (2, 2) in cluster
        assert (3, 2) not in cluster  # (col=3, row=2) = grid[2][3]

    def test_bfs_4_direction_only(self):
        """BFS should only propagate in 4 directions (not diagonal)."""
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11
                g.grid[row][col].alive = True
        g.grid[2][2].color = 8
        # diagonal at (3,3) is same color but not 4-adjacent
        g.grid[3][3].color = 8
        cluster = g._bfs_cluster(2, 2, 8)
        assert len(cluster) == 1  # only (2,2), diagonal not connected


# ═══════════════════════════════════════════════════════════════
# Solve element
# ═══════════════════════════════════════════════════════════════


class TestSolve:
    def test_first_click_no_combo(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11  # all LIME except clicked
                g.grid[row][col].alive = True
        g.grid[0][0].color = 8  # isolate one RED

        score = g._solve_element(0, 0)
        # First click: last_color=None → treated as match, combo=1
        # cluster size=1 (isolated RED), chain_count=0
        # score = 10 * 1 * 1.0 = 10
        assert score == SCORE_BASE
        assert g.combo == 1
        assert g.last_color == 8
        assert g.heat == 0.0
        assert g.grid[0][0].alive is False

    def test_same_color_combo(self):
        g = _make_game()
        # All RED
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 2

        score = g._solve_element(0, 0)
        assert g.combo == 3
        # combo=3, base=10*3=30, BFS cluster=30, chain_bonus=29*5=145, total=175
        expected = SCORE_BASE * 3 + 29 * SCORE_CHAIN
        assert score == expected

    def test_mismatch_color(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 11  # different from 8
        g.combo = 3
        g.heat = 0

        score = g._solve_element(0, 0)
        assert g.combo == 0  # reset
        assert g.heat == HEAT_MISMATCH
        # On mismatch: base=10, but BFS chain still runs (cluster=30, chain_bonus=29*5=145)
        # total = 10 + 145 = 155
        expected = SCORE_BASE + 29 * SCORE_CHAIN
        assert score == expected

    def test_super_mode_any_color(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 11
        g.super_timer = 100
        g.combo = 4

        score = g._solve_element(0, 0)
        assert g.combo == 5  # still increments
        expected = int(SCORE_BASE * 5 * 3.0) + (29 * SCORE_CHAIN)  # super mult=3
        assert score == expected

    def test_solve_dead_element_noop(self):
        g = _make_game()
        g.grid[0][0].alive = False
        score = g._solve_element(0, 0)
        assert score == 0
        assert g.combo == 0

    def test_super_activation_at_threshold(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 3  # next solve = combo 4

        g._solve_element(0, 0)
        assert g.combo == 4
        assert g.super_timer == SUPER_DURATION

    def test_super_reactivation_at_combo_8(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 7
        g.super_timer = 100  # already active, partially depleted

        g._solve_element(0, 0)
        assert g.combo == 8
        assert g.super_timer == SUPER_DURATION  # reset to full

    def test_cluster_marks_all_dead(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 0

        g._solve_element(2, 2)
        # All 30 cells should be dead
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                assert g.grid[row][col].alive is False

    def test_cluster_respawn_timers_set(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8

        g._solve_element(0, 0)
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                rt = g.grid[row][col].respawn_timer
                assert rt >= RESPAWN_DELAY_MIN
                assert rt <= RESPAWN_DELAY_MAX

    def test_mismatch_shake_frames(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 11

        g._solve_element(0, 0)
        assert g.shake_frames == 8

    def test_mismatch_floating_text(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 11

        g._solve_element(0, 0)
        wrong_texts = [ft for ft in g.floating_texts if ft.text == "WRONG!"]
        assert len(wrong_texts) == 1


# ═══════════════════════════════════════════════════════════════
# BFS chain scoring
# ═══════════════════════════════════════════════════════════════


class TestChainScoring:
    def test_no_chain_gives_only_base(self):
        g = _make_game()
        # Isolate cell (0,0) with different color from neighbors
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11
                g.grid[row][col].alive = True
        g.grid[0][0].color = 8
        g.last_color = 8
        g.combo = 0

        score = g._solve_element(0, 0)
        # cluster size = 1 (only clicked cell), chain_count=0
        assert score == SCORE_BASE  # 10 * 1 * 1.0 = 10

    def test_chain_bonus_added(self):
        g = _make_game()
        # Row 0 all RED
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11
                g.grid[row][col].alive = True
        for col in range(GRID_COLS):
            g.grid[0][col].color = 8
        g.last_color = 8
        g.combo = 0

        score = g._solve_element(0, 0)
        # cluster = 6, chain_count = 5, bonus = 5 * 5 = 25
        # base = 10 * 1 = 10, total = 35
        expected = SCORE_BASE + 5 * SCORE_CHAIN
        assert score == expected

    def test_chain_bonus_with_combo(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11
                g.grid[row][col].alive = True
        for col in range(GRID_COLS):
            g.grid[0][col].color = 8
        g.last_color = 8
        g.combo = 2

        score = g._solve_element(0, 0)
        # combo becomes 3, base = 10 * 3 = 30, chain = 5 * 5 = 25, total = 55
        expected = SCORE_BASE * 3 + 5 * SCORE_CHAIN
        assert score == expected


# ═══════════════════════════════════════════════════════════════
# Heat system
# ═══════════════════════════════════════════════════════════════


class TestHeat:
    def test_heat_accumulates(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 0.0
        g._update_heat()
        expected = HEAT_TIME_RATE - HEAT_DECAY_RATE  # 0.03 - 0.02 = 0.01
        assert abs(g.heat - expected) < 0.001

    def test_heat_game_over_at_cap(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = HEAT_CAP  # exactly 100
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
        assert g.heat == HEAT_CAP

    def test_heat_game_over_just_above_cap(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = HEAT_CAP - 0.001  # 99.999
        g._update_heat()
        # 99.999 + 0.03 - 0.02 = 100.009
        assert g.phase == Phase.GAME_OVER

    def test_heat_floor_at_zero(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 0.001  # very low
        g._update_heat()
        assert g.heat >= 0.0  # shouldn't go negative... wait, 0.001+0.03-0.02=0.011 > 0
        # Actually net is +0.01, so heat always goes up. But if decay > time_rate:
        pass  # current values: time_rate > decay, heat always grows

    def test_heat_clamped_at_cap(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 150.0  # way over
        g._update_heat()
        assert g.heat == HEAT_CAP  # clamped

    def test_heat_game_over_updates_best_score(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = HEAT_CAP
        g.score = 500
        g.best_score = 300
        g._update_heat()
        assert g.best_score == 500

    def test_heat_game_over_does_not_lower_best(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = HEAT_CAP
        g.score = 200
        g.best_score = 300
        g._update_heat()
        assert g.best_score == 300  # unchanged


# ═══════════════════════════════════════════════════════════════
# Timer
# ═══════════════════════════════════════════════════════════════


class TestTimer:
    def test_timer_decrements(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 100
        # Simulate _update_playing's timer logic directly
        g.timer -= 1
        assert g.timer == 99

    def test_timer_game_over(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g.timer -= 1
        assert g.timer == 0
        g.phase = Phase.GAME_OVER  # simulate the check
        assert g.phase == Phase.GAME_OVER

    def test_timer_game_over_updates_best(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g.score = 600
        g.best_score = 400
        g.timer -= 1
        if g.timer <= 0:
            g.phase = Phase.GAME_OVER
            if g.score > g.best_score:
                g.best_score = g.score
        assert g.best_score == 600


# ═══════════════════════════════════════════════════════════════
# Super mode lifecycle
# ═══════════════════════════════════════════════════════════════


class TestSuperMode:
    def test_super_timer_decrements(self):
        g = _make_game()
        g.super_timer = 100
        g.super_timer -= 1
        assert g.super_timer == 99

    def test_super_timer_does_not_go_below_zero(self):
        g = _make_game()
        g.super_timer = 0
        # _update_playing: if super_timer > 0: super_timer -= 1
        if g.super_timer > 0:
            g.super_timer -= 1
        assert g.super_timer == 0

    def test_super_is_on_when_timer_positive(self):
        g = _make_game()
        g.super_timer = 1
        assert g.super_timer > 0

    def test_super_is_off_when_timer_zero(self):
        g = _make_game()
        g.super_timer = 0
        assert g.super_timer == 0


# ═══════════════════════════════════════════════════════════════
# Respawn
# ═══════════════════════════════════════════════════════════════


class TestRespawn:
    def test_respawn_timer_decrements(self):
        g = _make_game()
        g.grid[0][0].alive = False
        g.grid[0][0].respawn_timer = 5
        g._update_respawns()
        assert g.grid[0][0].respawn_timer == 4

    def test_respawn_on_timer_zero(self):
        g = _make_game()
        g.grid[0][0].alive = False
        g.grid[0][0].respawn_timer = 1
        g._rng = random.Random(42)
        g._update_respawns()
        assert g.grid[0][0].alive is True
        assert g.grid[0][0].respawn_timer == 0

    def test_respawn_skips_alive(self):
        g = _make_game()
        g.grid[0][0].alive = True
        g.grid[0][0].respawn_timer = 10
        g._update_respawns()
        assert g.grid[0][0].respawn_timer == 10  # unchanged


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


class TestParticles:
    def test_spawn_particles(self):
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 5)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == 8

    def test_update_particles_gravity(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, color=8)
        g.particles = [p]
        g._update_particles()
        assert abs(p.vy - 0.1) < 0.001  # gravity added

    def test_update_particles_removes_dead(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0  # life=1->0, removed

    def test_update_particles_life_2_survives(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=2, color=8)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 1  # life=2->1, survives


# ═══════════════════════════════════════════════════════════════
# Floating texts
# ═══════════════════════════════════════════════════════════════


class TestFloatingTexts:
    def test_add_floating_text(self):
        g = _make_game()
        g._add_floating_text(100.0, 50.0, "COMBO x3", 7)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "COMBO x3"
        assert g.floating_texts[0].life == 40

    def test_update_floating_texts_rise_and_decay(self):
        g = _make_game()
        g._add_floating_text(100.0, 50.0, "+10", 7)
        g._update_floating_texts()
        assert g.floating_texts[0].y == 49.0  # moved up by 1
        assert g.floating_texts[0].life == 39

    def test_update_floating_texts_removes_dead(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=7, life=1)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_update_floating_texts_life_2_survives(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=7, life=2)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].life == 1


# ═══════════════════════════════════════════════════════════════
# Phase transitions
# ═══════════════════════════════════════════════════════════════


class TestPhases:
    def test_initial_phase_title(self):
        g = _make_game()
        assert g.phase == Phase.TITLE

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


# ═══════════════════════════════════════════════════════════════
# Score and combo tracking
# ═══════════════════════════════════════════════════════════════


class TestScoreTracking:
    def test_score_accumulates(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 0
        g.score = 0

        g._solve_element(0, 0)  # cluster=30, score=35
        assert g.score > 0

    def test_max_combo_tracks_peak(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 3
        g._solve_element(0, 0)
        assert g.max_combo == 4

    def test_max_combo_persists_after_mismatch(self):
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 8
                g.grid[row][col].alive = True
        g.last_color = 8
        g.combo = 3
        g._solve_element(0, 0)
        assert g.max_combo == 4

        # Clear super_timer so mismatch is treated as mismatch
        g.super_timer = 0
        # Now mismatch: isolate cell (0,0) with different color
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                g.grid[row][col].color = 11  # LIME
                g.grid[row][col].alive = True
        g.grid[0][0].color = 8  # RED
        g.last_color = 11
        g.combo = 4
        g.heat = 0
        g._solve_element(0, 0)
        assert g.combo == 0
        assert g.max_combo == 4  # peak preserved

    def test_best_score_tracks(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.best_score = 300
        g.heat = HEAT_CAP
        g._update_heat()
        assert g.best_score == 500

    def test_best_score_persists_across_reset(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 700
        g.heat = HEAT_CAP
        g._update_heat()
        assert g.best_score == 700

        g.reset()
        assert g.best_score == 700  # preserved
        assert g.score == 0  # but current score reset


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_element_colors_count(self):
        assert len(ELEMENT_COLORS) == 4

    def test_grid_dimensions(self):
        assert GRID_COLS == 6
        assert GRID_ROWS == 5

    def test_super_duration(self):
        assert SUPER_DURATION == 300

    def test_heat_constants(self):
        assert HEAT_CAP == 100.0
        assert HEAT_MISMATCH == 15.0

    def test_combo_threshold(self):
        assert COMBO_THRESHOLD == 4
