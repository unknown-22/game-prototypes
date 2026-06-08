"""test_imports.py — Headless logic tests for JAVELIN SURGE."""
import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/111_javelin_surge")
from main import Game, Zone, Javelin, Particle, Phase, RED, GREEN, DARK_BLUE, YELLOW, BROWN, ZONE_COLORS


def test_factory():
    g = Game._make_game()
    assert g.phase == Phase.TITLE
    assert g.attempt == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.best_dist == 0.0
    assert g.total_score == 0
    assert g.super_throw is False
    assert g.javelin is None
    assert len(g.zones) == 0
    assert len(g.particles) == 0


def test_reset():
    g = Game._make_game()
    g.phase = Phase.GAME_OVER
    g.attempt = 3
    g.combo = 5
    g.heat = 3
    g.best_dist = 42.0
    g.total_score = 999
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.attempt == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.best_dist == 0.0
    assert g.total_score == 0


def test_start_run_up():
    g = Game._make_game()
    g._start_run_up()
    assert g.phase == Phase.RUN_UP
    assert g.world_x == 0.0
    assert g.combo == 0
    assert g.super_throw is False
    assert g._last_matched_color is None
    assert len(g.zones) == 1
    assert g.zones_spawned == 1
    assert g.javelin is None


def test_zone_matching_hit():
    g = Game._make_game()
    g._start_run_up()
    g.zones = [Zone(x=78.0, color=RED, width=24)]
    matched = g._try_match_zone()
    assert matched == RED
    assert g.zones[0].hit is True


def test_zone_matching_miss():
    g = Game._make_game()
    g._start_run_up()
    # zone far from athlete
    g.zones = [Zone(x=200.0, color=GREEN, width=24)]
    matched = g._try_match_zone()
    assert matched is None
    assert g.zones[0].hit is False


def test_zone_matching_multiple_picks_leftmost():
    g = Game._make_game()
    g._start_run_up()
    g.zones = [
        Zone(x=78.0, color=RED, width=24),
        Zone(x=79.0, color=GREEN, width=24),
    ]
    matched = g._try_match_zone()
    assert matched == RED  # leftmost first
    assert g.zones[0].hit is True
    assert g.zones[1].hit is False


def test_zone_skips_already_hit():
    g = Game._make_game()
    g._start_run_up()
    g.zones = [Zone(x=78.0, color=RED, width=24, hit=True)]
    matched = g._try_match_zone()
    assert matched is None


def test_on_match_first():
    g = Game._make_game()
    g._start_run_up()
    g._on_match(RED)
    assert g.combo == 1
    assert g.heat == 0  # first match never adds heat
    assert g._last_matched_color == RED


def test_on_match_same_color_builds_combo():
    g = Game._make_game()
    g._start_run_up()
    g._on_match(RED)
    g._on_match(RED)
    assert g.combo == 2
    assert g.heat == 0


def test_on_match_wrong_color_resets_combo():
    g = Game._make_game()
    g._start_run_up()
    g._on_match(RED)
    g._on_match(RED)  # combo=2
    g._on_match(GREEN)  # wrong color
    assert g.combo == 1  # resets to 1 (new first match for green)
    assert g.heat == 1  # wrong color adds heat


def test_on_match_super_throw_activation():
    g = Game._make_game()
    g._start_run_up()
    for _ in range(4):
        g._on_match(RED)
    assert g.super_throw is True
    assert g.combo == 4


def test_on_miss():
    g = Game._make_game()
    g._start_run_up()
    g._on_match(RED)
    g._on_match(RED)  # combo=2
    g._on_miss()
    assert g.combo == 0
    assert g.heat == 1


def test_heat_accumulates():
    g = Game._make_game()
    g._start_run_up()
    # 3 wrong-color matches + 2 misses = 5 heat
    g._on_match(RED)
    g._on_match(GREEN)  # heat=1
    g._on_match(DARK_BLUE)  # heat=2
    g._on_match(YELLOW)  # heat=3
    g._on_miss()  # heat=4
    g._on_miss()  # heat=5
    assert g.heat == 5


def test_heat_capped():
    g = Game._make_game()
    g._start_run_up()
    g.heat = 5
    g._on_match(RED)
    g._on_match(GREEN)
    assert g.heat == 5  # capped at MAX_HEAT


def test_check_heat_game_over():
    g = Game._make_game()
    g._start_run_up()
    g.heat = 5
    assert g.check_heat_game_over() is True
    assert g.phase == Phase.GAME_OVER


def test_check_heat_not_game_over():
    g = Game._make_game()
    g._start_run_up()
    g.heat = 3
    assert g.check_heat_game_over() is False
    assert g.phase == Phase.RUN_UP


def test_enter_throw_phase():
    g = Game._make_game()
    g._start_run_up()
    g._enter_throw_phase()
    assert g.phase == Phase.THROW


def test_throw_javelin_normal():
    g = Game._make_game()
    g._start_run_up()
    g._throw_javelin(0.5, 3.0)
    assert g.phase == Phase.FLIGHT
    assert g.javelin is not None
    assert g.javelin.color == DARK_BLUE  # normal throw color
    assert g.javelin.x == float(g.THROW_LINE_X)
    assert g.javelin.landed is False


def test_throw_javelin_super():
    g = Game._make_game()
    g._start_run_up()
    g.super_throw = True
    g._throw_javelin(0.5, 3.0)
    assert g.javelin is not None
    assert g.javelin.color == YELLOW  # super throw color


def test_compute_flight_normal():
    g = Game._make_game()
    g.super_throw = False
    j = Javelin(x=260.0, y=146.0, vx=3.0, vy=-2.0, angle=0.5, power=2.0, color=DARK_BLUE)
    dist = g._compute_flight(j)
    assert dist > 0.0
    assert dist < 10.0  # reasonable range


def test_compute_flight_super_multiplier():
    g = Game._make_game()
    j = Javelin(x=260.0, y=146.0, vx=3.0, vy=-2.0, angle=0.5, power=2.0, color=DARK_BLUE)
    g.super_throw = False
    dist_base = g._compute_flight(j)
    g.super_throw = True
    dist_super = g._compute_flight(j)
    assert abs(dist_super - dist_base * g.SUPER_DIST_MULT) < 0.001


def test_compute_flight_zero_or_negative_vx():
    g = Game._make_game()
    g.super_throw = False
    j = Javelin(x=260.0, y=146.0, vx=0.0, vy=-5.0, angle=0.0, power=2.0, color=DARK_BLUE)
    dist = g._compute_flight(j)
    assert dist >= 0.0


def test_update_flight_lands():
    g = Game._make_game()
    g._start_run_up()
    g._throw_javelin(0.3, 4.0)
    # simulate until landed
    for _ in range(200):
        g._update_flight()
        if g.javelin is not None and g.javelin.landed:
            break
    assert g.javelin is not None
    assert g.javelin.landed is True
    assert g.phase == Phase.RESULT


def test_on_landing_sets_score():
    g = Game._make_game()
    g._start_run_up()
    g._throw_javelin(0.3, 4.0)
    for _ in range(200):
        g._update_flight()
        if g.phase == Phase.RESULT:
            break
    assert g.current_dist > 0
    assert g.current_score > 0
    assert g.total_score > 0


def test_on_landing_updates_best_dist():
    g = Game._make_game()
    g._start_run_up()
    g._throw_javelin(0.3, 4.0)
    for _ in range(200):
        g._update_flight()
        if g.phase == Phase.RESULT:
            break
    best1 = g.best_dist
    assert best1 > 0

    # second throw with higher power
    g._start_run_up()
    g._throw_javelin(0.4, 8.0)
    for _ in range(200):
        g._update_flight()
        if g.phase == Phase.RESULT:
            break
    assert g.best_dist >= best1


def test_on_landing_reduces_heat():
    g = Game._make_game()
    g._start_run_up()
    g.heat = 3
    g._throw_javelin(0.3, 4.0)
    for _ in range(200):
        g._update_flight()
        if g.phase == Phase.RESULT:
            break
    assert g.heat == 2  # heat - 1


def test_on_landing_super_score_multiplier():
    g = Game._make_game()
    g._start_run_up()
    g.super_throw = True
    g._throw_javelin(0.3, 4.0)
    for _ in range(200):
        g._update_flight()
        if g.phase == Phase.RESULT:
            break
    dist_score = int(g.current_dist * 10)
    expected = dist_score * g.SUPER_SCORE_MULT
    assert g.current_score == expected


def test_spawn_particles():
    g = Game._make_game()
    g._spawn_particles(200.0, 160.0, BROWN, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.life >= 10
        assert p.life <= 20


def test_update_particles():
    g = Game._make_game()
    g._spawn_particles(200.0, 160.0, BROWN, 5)
    g._update_particles()
    for p in g.particles:
        assert p.life >= 9  # decremented by 1


def test_update_particles_removes_dead():
    g = Game._make_game()
    g.particles = [
        Particle(x=0, y=0, vx=0, vy=0, life=1, color=BROWN),
        Particle(x=0, y=0, vx=0, vy=0, life=2, color=BROWN),
    ]
    g._update_particles()
    # particle with life=1 decremented to 0, removed
    assert len(g.particles) == 1


def test_spawn_match_particles():
    g = Game._make_game()
    g._spawn_match_particles(RED)
    assert len(g.particles) == 6


def test_attempt_counting():
    g = Game._make_game()
    g._start_run_up()
    assert g.attempt == 0
    g._next_attempt()
    assert g.attempt == 1
    assert g.phase == Phase.RUN_UP


def test_max_attempts_game_over():
    g = Game._make_game()
    g._start_run_up()
    for i in range(5):
        g._next_attempt()
    assert g.phase == Phase.GAME_OVER
    assert g.attempt == 5


def test_next_attempt_heat_game_over():
    g = Game._make_game()
    g._start_run_up()
    g.heat = 5
    g._next_attempt()
    assert g.phase == Phase.GAME_OVER


def test_try_advance_result_with_timer():
    g = Game._make_game()
    g._start_run_up()
    g.phase = Phase.RESULT
    g.result_timer = 50
    g.try_advance_result()
    assert g.result_timer == 49
    assert g.phase == Phase.RESULT


def test_try_advance_result_timer_expired():
    g = Game._make_game()
    g._start_run_up()
    g.phase = Phase.RESULT
    g.result_timer = 1
    g.try_advance_result()
    assert g.result_timer == 0
    g.try_advance_result()
    assert g.phase == Phase.RUN_UP
    assert g.attempt == 1


def test_update_zones_moves_zones():
    g = Game._make_game()
    g._start_run_up()
    world_before = g.world_x
    g._update_zones()
    assert g.world_x > world_before
    assert g.world_x == world_before + g.RUN_SPEED


def test_update_zones_marks_passed():
    g = Game._make_game()
    g._start_run_up()
    # place a zone far to the left (already passed)
    g.zones = [Zone(x=float(g.ATHLETE_X) - 100.0, color=RED, width=24)]
    g._update_zones()
    assert g.zones[0].passed is True
    assert g.combo == 0  # miss due to passing
    assert g.heat == 1


def test_update_zones_spawns_new():
    g = Game._make_game()
    g._start_run_up()
    g.zones_spawned = 1
    g.zones = []
    g._update_zones()
    assert len(g.zones) == 1


def test_update_zones_enters_throw_when_done():
    g = Game._make_game()
    g._start_run_up()
    g.zones_spawned = g.zone_target_count  # all spawned
    g.zones = []  # all consumed
    g._update_zones()
    assert g.phase == Phase.THROW


def test_spawn_zone():
    g = Game._make_game()
    g._start_run_up()
    z = g._spawn_zone()
    assert z.color in ZONE_COLORS
    assert z.width == 24
    assert z.hit is False
    assert z.passed is False
    assert g.zones_spawned == 2  # _start_run_up spawned 1, then we spawned 1


def test_max_combo_tracking():
    g = Game._make_game()
    g._start_run_up()
    g._on_match(RED)  # combo=1, max=1
    g._on_match(RED)  # combo=2, max=2
    g._on_match(RED)  # combo=3, max=3
    g._on_match(GREEN)  # combo=1, max stays 3
    g._on_match(GREEN)  # combo=2, max stays 3
    assert g.max_combo == 3


def test_super_throw_stays_after_activation():
    g = Game._make_game()
    g._start_run_up()
    for _ in range(4):
        g._on_match(RED)
    assert g.super_throw is True
    # additional same-color matches don't turn it off
    g._on_match(RED)
    assert g.super_throw is True


def test_runway_length():
    g = Game._make_game()
    assert g.runway_length == 400.0
    assert g.zone_target_count == 8


def test_zone_color_names():
    from main import ZONE_COLOR_NAMES
    assert ZONE_COLOR_NAMES[RED] == "RED"
    assert ZONE_COLOR_NAMES[GREEN] == "GRN"
    assert ZONE_COLOR_NAMES[DARK_BLUE] == "BLU"
    assert ZONE_COLOR_NAMES[YELLOW] == "YEL"


def test_color_constants():
    assert RED == 8
    assert GREEN == 3
    assert DARK_BLUE == 5
    assert YELLOW == 10
    assert len(ZONE_COLORS) == 4


def test_phase_enum_values():
    assert Phase.TITLE == "TITLE"
    assert Phase.RUN_UP == "RUN_UP"
    assert Phase.THROW == "THROW"
    assert Phase.FLIGHT == "FLIGHT"
    assert Phase.RESULT == "RESULT"
    assert Phase.GAME_OVER == "GAME_OVER"


if __name__ == "__main__":
    import traceback

    tests = [
        (name, obj)
        for name, obj in list(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"  PASS  {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    if failed > 0:
        sys.exit(1)
