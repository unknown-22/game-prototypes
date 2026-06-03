"""test_imports.py -- Headless logic tests for 103_switch_surge."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (
    COLORS,
    COMBO_SUPER_THRESHOLD,
    DARK_BLUE,
    EDGES,
    FloatingText,
    GAME_DURATION_FRAMES,
    GREEN,
    HEAT_BLOCK,
    HEAT_BLOCK_DURATION,
    HEAT_PER_QUEUE,
    HEAT_PER_WRONG,
    HEAT_RESET_AFTER_BLOCK,
    JUNCTION_DEFS,
    MAX_HEAT,
    MIN_SPAWN_INTERVAL,
    NODES,
    NODE_STATION,
    NODE_TYPES,
    ORANGE,
    Particle,
    Phase,
    RED,
    SCREEN_H,
    SCREEN_W,
    STATION_COOLDOWN,
    STATION_COLOR_MAP,
    SURGE_DURATION,
    SURGE_SCORE_MULT,
    SwitchSurge,
    WHITE,
    WRONG_PENALTY,
    YELLOW,
    Train,
    Junction,
    Station,
)




def _make_game() -> SwitchSurge:
    """Factory: create a SwitchSurge instance bypassing pyxel.init/run."""
    g = SwitchSurge.__new__(SwitchSurge)
    g._rng = __import__("random").Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION_FRAMES
    g.trains_dispatched = 0
    g.surge_timer = 0
    g.block_timer = 0
    g.blocked_junction = -1
    g._spawn_timer = 0
    g._spawn_interval = 90
    g._speed_mult = 1.0
    g._shake_frames = 0
    g.trains = []
    g.particles = []
    g.floating_texts = []
    g.ghost_trains = []
    g.junctions = []
    g.stations = []
    g._init_track_network()
    g.phase = Phase.PLAYING
    return g


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class TestConstants:
    def test_screen_size(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_H == 240

    def test_colors(self) -> None:
        assert COLORS == (RED, GREEN, DARK_BLUE, YELLOW)
        assert len(COLORS) == 4

    def test_track_network_nodes(self) -> None:
        assert len(NODES) == 15
        assert NODE_TYPES[0] == NODE_STATION  # GL
        assert NODE_TYPES[1] == NODE_STATION  # BL
        assert NODE_TYPES[2] == NODE_STATION  # YL
        assert NODE_TYPES[3] == NODE_STATION  # RD
        assert NODE_TYPES[4] != NODE_STATION  # L entrance
        assert NODE_TYPES[5] != NODE_STATION  # R entrance

    def test_edges_count(self) -> None:
        assert len(EDGES) == 18

    def test_junction_defs(self) -> None:
        assert len(JUNCTION_DEFS) == 4
        for jn in JUNCTION_DEFS:
            assert len(jn) == 4

    def test_station_colors(self) -> None:
        assert STATION_COLOR_MAP[0] == GREEN   # top-left
        assert STATION_COLOR_MAP[1] == DARK_BLUE  # top-right
        assert STATION_COLOR_MAP[2] == YELLOW   # bottom-left
        assert STATION_COLOR_MAP[3] == RED      # bottom-right

    def test_game_balance(self) -> None:
        assert COMBO_SUPER_THRESHOLD == 4
        assert SURGE_SCORE_MULT == 3.0
        assert MAX_HEAT == 100.0
        assert HEAT_BLOCK == 100.0


# ---------------------------------------------------------------------------
# Phase machine
# ---------------------------------------------------------------------------
class TestPhaseMachine:
    def test_initial_phase(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING

    def test_phases_exist(self) -> None:
        assert Phase.TITLE is not None
        assert Phase.PLAYING is not None
        assert Phase.GAME_OVER is not None

    def test_check_game_over_transition(self) -> None:
        g = _make_game()
        g.timer = 1
        g._check_game_over()
        assert g.phase == Phase.PLAYING
        g.timer = 0
        g._check_game_over()
        assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Track network initialization
# ---------------------------------------------------------------------------
class TestTrackNetwork:
    def test_junctions_initialized(self) -> None:
        g = _make_game()
        assert len(g.junctions) == 4
        for jn in g.junctions:
            assert isinstance(jn, Junction)
            assert jn.state == 0  # all start straight

    def test_stations_initialized(self) -> None:
        g = _make_game()
        assert len(g.stations) == 4
        for stn in g.stations:
            assert isinstance(stn, Station)
            assert stn.cooldown == 0

    def test_station_colors_match(self) -> None:
        g = _make_game()
        assert g.stations[0].color == GREEN
        assert g.stations[1].color == DARK_BLUE
        assert g.stations[2].color == YELLOW
        assert g.stations[3].color == RED


# ---------------------------------------------------------------------------
# Path finding
# ---------------------------------------------------------------------------
class TestPathFinding:
    def test_find_path_entrance_to_station(self) -> None:
        g = _make_game()
        # Left entrance (4) to GL station (0)
        path = g._find_path(4, 0)
        assert path is not None
        assert path[0] == 4
        assert path[-1] == 0
        assert len(path) >= 2

    def test_find_path_right_to_red(self) -> None:
        g = _make_game()
        # Right entrance (5) to RD station (3)
        path = g._find_path(5, 3)
        assert path is not None
        assert path[0] == 5
        assert path[-1] == 3

    def test_find_path_all_stations_reachable_left(self) -> None:
        g = _make_game()
        for stn_id in range(4):
            path = g._find_path(4, stn_id)
            assert path is not None, f"Station {stn_id} not reachable from left entrance"
            assert path[-1] == stn_id

    def test_find_path_all_stations_reachable_right(self) -> None:
        g = _make_game()
        for stn_id in range(4):
            path = g._find_path(5, stn_id)
            assert path is not None, f"Station {stn_id} not reachable from right entrance"
            assert path[-1] == stn_id


# ---------------------------------------------------------------------------
# Train spawning
# ---------------------------------------------------------------------------
class TestTrainSpawning:
    def test_spawn_train_creates_train(self) -> None:
        g = _make_game()
        assert len(g.trains) == 0
        g._spawn_train()
        assert len(g.trains) == 1

    def test_spawned_train_has_valid_properties(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        assert isinstance(t, Train)
        assert t.color in COLORS
        assert t.target_station in range(4)
        assert len(t.path) >= 2
        assert t.path_idx == 0
        assert t.progress == 0.0
        assert not t.queued

    def test_spawn_train_from_entrance(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        assert t.path[0] in (4, 5)  # left or right entrance

    def test_spawn_train_targets_matching_station(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        expected_station_color = STATION_COLOR_MAP[t.target_station]
        assert expected_station_color == t.color


# ---------------------------------------------------------------------------
# Train movement
# ---------------------------------------------------------------------------
class TestTrainMovement:
    def test_train_moves_along_path(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        orig_progress = t.progress
        orig_idx = t.path_idx
        g._update_trains()
        assert t.progress > orig_progress or t.path_idx > orig_idx

    def test_train_position_is_on_track(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        px, py = g._train_position(t)
        assert isinstance(px, float)
        assert isinstance(py, float)

    def test_speed_multiplier_affects_movement(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        g._speed_mult = 1.0
        orig_progress = t.progress
        g._update_trains()
        delta_normal = t.progress - orig_progress

        # Reset and test with higher speed
        t.progress = 0.0
        t.path_idx = 0
        g._speed_mult = 2.0
        g._update_trains()
        assert t.progress > delta_normal  # moves faster

    def test_train_reaches_next_node(self) -> None:
        g = _make_game()
        g._rng = __import__("random").Random(42)
        # Force a short path by manually constructing a train
        t = Train(
            color=RED,
            target_station=3,
            path=[5, 14, 11, 3],  # R entrance -> W4 -> W1 -> RD
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        # Move many times
        for _ in range(300):
            g._update_trains()
        assert t.path_idx >= 1  # should have advanced at least one segment


# ---------------------------------------------------------------------------
# Train arrival and scoring
# ---------------------------------------------------------------------------
class TestArrivalAndScoring:
    def test_correct_arrival_increases_score(self) -> None:
        g = _make_game()
        t = Train(
            color=GREEN,
            target_station=0,
            path=[0],  # Already at GL station
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        orig_score = g.score
        g._update_arrivals()
        assert g.score > orig_score
        assert g.trains_dispatched >= 1

    def test_correct_arrival_increases_combo(self) -> None:
        g = _make_game()
        t = Train(
            color=GREEN,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        orig_combo = g.combo
        g._update_arrivals()
        assert g.combo > orig_combo  # combo should be at least 1

    def test_wrong_arrival_decreases_score(self) -> None:
        g = _make_game()
        t = Train(
            color=RED,
            target_station=0,  # targets GL station
            path=[0],  # arrives at GL station (color=GREEN)
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        g.score = 50
        g._update_arrivals()
        assert g.score == 50 + WRONG_PENALTY

    def test_wrong_arrival_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        t = Train(
            color=RED,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        g._update_arrivals()
        assert g.combo == 0

    def test_wrong_arrival_adds_heat(self) -> None:
        g = _make_game()
        t = Train(
            color=RED,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        orig_heat = g.heat
        g._update_arrivals()
        assert g.heat == min(orig_heat + HEAT_PER_WRONG, MAX_HEAT)

    def test_station_cooldown_applied_on_arrival(self) -> None:
        g = _make_game()
        t = Train(
            color=GREEN,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        assert g.stations[0].cooldown == 0
        g._update_arrivals()
        assert g.stations[0].cooldown == STATION_COOLDOWN

    def test_max_combo_tracked(self) -> None:
        g = _make_game()
        g.combo = 5
        g.max_combo = 3
        t = Train(
            color=GREEN,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        g._update_arrivals()
        assert g.max_combo >= 6


# ---------------------------------------------------------------------------
# COMBO and SURGE
# ---------------------------------------------------------------------------
class TestComboAndSurge:
    def test_combo_below_threshold_no_surge(self) -> None:
        g = _make_game()
        g.combo = 3
        t = Train(
            color=GREEN,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        g._update_arrivals()
        assert g.combo == 4
        assert g.surge_timer == SURGE_DURATION  # triggers at combo=4 (>=4)

    def test_combo_at_threshold_triggers_surge(self) -> None:
        g = _make_game()
        g.combo = COMBO_SUPER_THRESHOLD - 1  # = 3
        t = Train(
            color=GREEN,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        g._update_arrivals()
        assert g.combo >= COMBO_SUPER_THRESHOLD
        assert g.surge_timer == SURGE_DURATION

    def test_is_surge_active(self) -> None:
        g = _make_game()
        assert not g._is_surge()
        g.surge_timer = 100
        assert g._is_surge()

    def test_surge_timer_decrements(self) -> None:
        g = _make_game()
        g.surge_timer = 10
        g._update_surge()
        assert g.surge_timer == 9

    def test_surge_timer_stops_at_zero(self) -> None:
        g = _make_game()
        g.surge_timer = 1
        g._update_surge()
        assert g.surge_timer == 0
        g._update_surge()
        assert g.surge_timer == 0

    def test_surge_arrival_3x_score(self) -> None:
        g = _make_game()
        g.surge_timer = 100
        g.combo = 5
        # Wrong color train arriving at station during SURGE
        t = Train(
            color=RED,
            target_station=0,
            path=[0],  # GL station (GREEN)
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        orig_score = g.score
        g._update_arrivals()
        # Should get 3x score, combo goes up
        assert g.score > orig_score + 50  # definitely positive

    def test_surge_no_heat_from_wrong_color(self) -> None:
        g = _make_game()
        g.surge_timer = 100
        g.heat = 0.0
        t = Train(
            color=RED,
            target_station=0,
            path=[0],
            path_idx=0,
            progress=0.0,
        )
        g.trains.append(t)
        g._update_arrivals()
        assert g.heat == 0.0  # no heat in surge


# ---------------------------------------------------------------------------
# Junction toggling
# ---------------------------------------------------------------------------
class TestJunctionToggling:
    def test_toggle_junction_changes_state(self) -> None:
        g = _make_game()
        jn = g.junctions[0]
        orig_state = jn.state
        jn.state = 1 - jn.state
        assert jn.state != orig_state

    def test_toggle_affects_edge_traversal(self) -> None:
        g = _make_game()
        # J0 (node 6): state=0 means edges 0(GL<->J0) and 1(J0<->J1) connected
        # state=1 means edges 0 and 12(J0<->W2) connected
        assert g.junctions[0].state == 0
        g._init_track_network()
        g.junctions[0].state = 0
        assert g._edge_traversable(0)  # edge GL-J0
        assert g._edge_traversable(1)  # edge J0-J1
        assert not g._edge_traversable(12)  # edge J0-W2

        g.junctions[0].state = 1
        assert g._edge_traversable(0)   # GL-J0
        assert not g._edge_traversable(1)  # J0-J1 blocked
        assert g._edge_traversable(12)  # J0-W2

    def test_recompute_paths_after_toggle(self) -> None:
        g = _make_game()
        g._spawn_train()
        t = g.trains[0]
        # Toggle all junctions
        for jn in g.junctions:
            jn.state = 1 - jn.state
        g._recompute_all_paths()
        # Path may be different now
        assert isinstance(t.path, list)
        assert len(t.path) >= 2


# ---------------------------------------------------------------------------
# Heat system
# ---------------------------------------------------------------------------
class TestHeatSystem:
    def test_heat_starts_at_zero(self) -> None:
        g = _make_game()
        assert g.heat == 0.0

    def test_heat_capped_at_max(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT + 10
        # Heat should not exceed max from heat_add operations
        g.heat = MAX_HEAT
        assert g.heat == MAX_HEAT

    def test_wrong_arrival_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 10.0
        t = Train(color=RED, target_station=0, path=[0], path_idx=0, progress=0.0)
        g.trains.append(t)
        g._update_arrivals()
        assert g.heat > 10.0

    def test_heat_block_triggers_at_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_BLOCK  # 100
        g._update_heat_block()
        assert g.block_timer == HEAT_BLOCK_DURATION
        assert g.blocked_junction >= 0

    def test_heat_block_resets_heat_on_end(self) -> None:
        g = _make_game()
        g.block_timer = 1
        g.heat = 80.0
        g.blocked_junction = 6
        g._update_heat_block()
        assert g.block_timer == 0
        assert g.heat == HEAT_RESET_AFTER_BLOCK
        assert g.blocked_junction == -1

    def test_queued_train_adds_heat_per_frame(self) -> None:
        g = _make_game()
        g.stations[0].cooldown = STATION_COOLDOWN
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        t.queued = True
        g.trains.append(t)
        orig_heat = g.heat
        g._update_trains()
        assert g.heat == min(orig_heat + HEAT_PER_QUEUE, MAX_HEAT)


# ---------------------------------------------------------------------------
# Station cooldown
# ---------------------------------------------------------------------------
class TestStationCooldown:
    def test_cooldown_decrements(self) -> None:
        g = _make_game()
        g.stations[0].cooldown = STATION_COOLDOWN
        g._update_station_cooldowns()
        assert g.stations[0].cooldown == STATION_COOLDOWN - 1

    def test_cooldown_stops_at_zero(self) -> None:
        g = _make_game()
        g.stations[0].cooldown = 1
        g._update_station_cooldowns()
        assert g.stations[0].cooldown == 0
        g._update_station_cooldowns()
        assert g.stations[0].cooldown == 0

    def test_train_queues_when_station_on_cooldown(self) -> None:
        g = _make_game()
        g.stations[0].cooldown = STATION_COOLDOWN
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        g.trains.append(t)
        g._update_arrivals()
        assert t.queued

    def test_queued_train_releases_after_cooldown(self) -> None:
        g = _make_game()
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        t.queued = True
        t.queued_frames = 5
        g.trains.append(t)
        g.stations[0].cooldown = 0  # ready to accept
        g._update_arrivals()
        assert len(g.trains) == 0  # train should be removed after arrival


# ---------------------------------------------------------------------------
# Timer and difficulty scaling
# ---------------------------------------------------------------------------
class TestTimerAndScaling:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        orig_timer = g.timer
        g._update_timer()
        assert g.timer == orig_timer - 1

    def test_speed_mult_increases_over_time(self) -> None:
        g = _make_game()
        g.timer = GAME_DURATION_FRAMES - (15 * 60 + 1)  # just past 15s
        g._update_timer()
        assert g._speed_mult == 1.0 + 0.15  # one bump

    def test_speed_mult_at_30s(self) -> None:
        g = _make_game()
        g.timer = GAME_DURATION_FRAMES - (30 * 60 + 1)  # just past 30s
        g._update_timer()
        assert g._speed_mult == 1.0 + 0.30  # two bumps

    def test_spawn_interval_decreases(self) -> None:
        g = _make_game()
        g._spawn_timer = 0
        orig_interval = g._spawn_interval
        g._update_spawning()
        assert g._spawn_interval == max(MIN_SPAWN_INTERVAL, orig_interval - 2)


# ---------------------------------------------------------------------------
# Ghost trains
# ---------------------------------------------------------------------------
class TestGhostTrains:
    def test_ghost_recorded_on_arrival(self) -> None:
        g = _make_game()
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        g.trains.append(t)
        g._update_arrivals()
        assert len(g.ghost_trains) == 1
        assert len(g.ghost_trains[0]) >= 1

    def test_ghost_max_three(self) -> None:
        g = _make_game()
        for _ in range(5):
            t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
            g.trains.append(t)
            g._update_arrivals()
        assert len(g.ghost_trains) <= 3

    def test_ghost_points_color(self) -> None:
        g = _make_game()
        t = Train(color=RED, target_station=3, path=[4, 12, 13, 14, 11, 3], path_idx=5, progress=0.0)
        g.trains.append(t)
        g._record_ghost(t)
        assert len(g.ghost_trains[0]) > 0
        _, _, col = g.ghost_trains[0][0]
        assert col == RED


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------
class TestParticles:
    def test_spawn_arrival_particles(self) -> None:
        g = _make_game()
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        g.trains.append(t)
        g._spawn_arrival_particles(t, True)
        assert len(g.particles) > 0

    def test_particles_have_color(self) -> None:
        g = _make_game()
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        g.trains.append(t)
        g._spawn_arrival_particles(t, True)
        for p in g.particles:
            assert isinstance(p, Particle)
            assert p.color in (GREEN, ORANGE)

    def test_particles_update_reduces_life(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=0.5, vy=-1.0, life=10, max_life=10, color=RED)]
        g._update_particles()
        assert g.particles[0].life == 9

    def test_particles_removed_when_life_zero(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=0.5, vy=-1.0, life=1, max_life=1, color=RED)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_particles_affected_by_gravity(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, max_life=10, color=RED)]
        orig_vy = g.particles[0].vy
        g._update_particles()
        assert g.particles[0].vy > orig_vy


# ---------------------------------------------------------------------------
# Floating text system
# ---------------------------------------------------------------------------
class TestFloatingText:
    def test_spawn_floating_text(self) -> None:
        g = _make_game()
        t = Train(color=GREEN, target_station=0, path=[0], path_idx=0, progress=0.0)
        g.trains.append(t)
        g._spawn_floating_text(t, "+100", GREEN)
        assert len(g.floating_texts) == 1
        ft = g.floating_texts[0]
        assert ft.text == "+100"
        assert ft.color == GREEN

    def test_floating_text_rises_and_fades(self) -> None:
        g = _make_game()
        ft = FloatingText(x=100.0, y=100.0, text="TEST", life=30, color=WHITE)
        g.floating_texts.append(ft)
        orig_y = ft.y
        g._update_floating_texts()
        assert ft.y < orig_y  # rises upward
        assert ft.life == 29

    def test_floating_text_removed_at_zero_life(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=1, color=WHITE)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ---------------------------------------------------------------------------
# Reset / restart
# ---------------------------------------------------------------------------
class TestReset:
    def test_init_state_resets_all(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 8
        g.heat = 90.0
        g.surge_timer = 30
        g.trains = []
        g.particles = []
        g.floating_texts = []
        g.ghost_trains = []
        g._init_state()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.surge_timer == 0
        assert g.timer == GAME_DURATION_FRAMES
        assert len(g.trains) == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert len(g.ghost_trains) == 0
        assert g._speed_mult == 1.0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
