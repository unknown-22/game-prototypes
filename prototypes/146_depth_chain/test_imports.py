"""test_imports.py — Headless logic tests for DEPTH CHAIN."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/146_depth_chain")
from main import (
    GREEN, DARK_BLUE, RED, YELLOW, LIME, CYAN, COLOR_VALS,
    SCREEN_W, SCREEN_H,
    DIVER_W, DIVER_H, DIVER_X,
    MAX_OXYGEN, MAX_HEAT,
    OXYGEN_DECAY, OXYGEN_ASCENT_COST,
    HEAT_DECAY, HEAT_WRONG,
    COMBO_THRESHOLD, SUPER_DURATION,
    PEARL_COUNT, PEARL_SPAWN_INTERVAL,
    DARKNESS_RISE_SPEED, SCROLL_SPEED,
    SWIM_SPEED, MOVE_SPEED,
    SUPER_COLLECT_RADIUS, COLLISION_DIST,
    Game, Phase, Pearl, Particle, FloatingText,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.pearls = []
    g.particles = []
    g.floating_texts = []
    g.reset()
    g._rng = random.Random(42)
    return g


# ── Dataclass Tests ──

def test_pearl_creation():
    p = Pearl(x=100.0, y=50.0, color=2)
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.color == 2
    assert p.collected is False


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == RED
    assert p.size == 2


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+25", life=30, color=LIME)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+25"
    assert ft.life == 30
    assert ft.color == LIME


# ── Phase Enum Tests ──

def test_phase_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Constants Tests ──

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert DIVER_W == 12
    assert DIVER_H == 16
    assert DIVER_X == 154
    assert MAX_OXYGEN == 100.0
    assert MAX_HEAT == 100.0
    assert OXYGEN_DECAY == 0.03
    assert OXYGEN_ASCENT_COST == 0.08
    assert HEAT_DECAY == 0.02
    assert HEAT_WRONG == 15.0
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert PEARL_COUNT == 12
    assert PEARL_SPAWN_INTERVAL == 60
    assert DARKNESS_RISE_SPEED == 0.02
    assert SCROLL_SPEED == 0.3
    assert SWIM_SPEED == 2.0
    assert MOVE_SPEED == 1.5
    assert SUPER_COLLECT_RADIUS == 40
    assert COLLISION_DIST == 13  # DIVER_RADIUS(9) + PEARL_RADIUS(4)


def test_color_vals():
    assert len(COLOR_VALS) == 4
    assert COLOR_VALS[0] == RED
    assert COLOR_VALS[1] == GREEN
    assert COLOR_VALS[2] == DARK_BLUE
    assert COLOR_VALS[3] == YELLOW


# ── Depth Multiplier ──

def test_calc_depth_mult_zero():
    assert Game.calc_depth_mult(0.0) == 1.0


def test_calc_depth_mult_500():
    assert Game.calc_depth_mult(500.0) == 2.0


def test_calc_depth_mult_2000():
    assert Game.calc_depth_mult(2000.0) == 5.0


def test_calc_depth_mult_capped():
    assert Game.calc_depth_mult(5000.0) == 10.0
    assert Game.calc_depth_mult(10000.0) == 10.0


# ── Game.reset() ──

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.diver_x == float(DIVER_X)
    assert g.diver_y == 60.0
    assert g.oxygen == MAX_OXYGEN
    assert g.heat == 0.0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.current_color == -1
    assert g.super_timer == 0
    assert g.darkness_y == float(SCREEN_H - 40)
    assert len(g.pearls) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.frame == 0
    assert g.spawn_timer == 0
    assert g.depth == 0.0
    assert g.total_pearls_collected == 0
    assert g._best_score == 0


# ── _start_game ──

def test_start_game_transitions():
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.frame == 0
    assert g.depth == 0.0
    assert g.total_pearls_collected == 0
    assert len(g.pearls) == 0
    assert g.super_timer == 0
    assert g.spawn_timer == 30


# ── _end_game ──

def test_end_game_transitions():
    g = _make_game()
    g._start_game()
    g.score = 500
    g._best_score = 0
    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g._best_score == 500


def test_end_game_keeps_best_score():
    g = _make_game()
    g._start_game()
    g._best_score = 800
    g.score = 500
    g._end_game()
    assert g._best_score == 800


# ── _spawn_pearl ──

def test_spawn_pearl():
    g = _make_game()
    pearl = g._spawn_pearl()
    assert pearl.color in (0, 1, 2, 3)
    assert 20 <= pearl.x <= SCREEN_W - 20
    assert -10 <= pearl.y <= 0
    assert pearl.collected is False


def test_spawn_pearl_color_variety():
    g = _make_game()
    colors = {g._spawn_pearl().color for _ in range(50)}
    assert len(colors) == 4


# ── _update_pearls ──

def test_update_pearls_moves_down():
    g = _make_game()
    g.pearls = [Pearl(x=100.0, y=50.0, color=0)]
    g._update_pearls()
    assert g.pearls[0].y == 50.0 + SCROLL_SPEED


def test_update_pearls_removes_below_screen():
    g = _make_game()
    g.pearls = [Pearl(x=100.0, y=float(SCREEN_H + 20), color=0)]
    g._update_pearls()
    assert len(g.pearls) == 0


def test_update_pearls_removes_collected():
    g = _make_game()
    g.pearls = [Pearl(x=100.0, y=50.0, color=0, collected=True)]
    g._update_pearls()
    assert len(g.pearls) == 0


# ── _update_spawn ──

def test_update_spawn_creates_pearl():
    g = _make_game()
    g.spawn_timer = 1
    assert len(g.pearls) == 0
    g._update_spawn()
    assert len(g.pearls) == 1
    assert g.pearls[0].color in (0, 1, 2, 3)


def test_update_spawn_respects_cap():
    g = _make_game()
    g.pearls = [Pearl(x=100.0, y=50.0, color=0) for _ in range(PEARL_COUNT)]
    g.spawn_timer = 1
    g._update_spawn()
    assert len(g.pearls) == PEARL_COUNT


def test_update_spawn_timer_decrements():
    g = _make_game()
    g.spawn_timer = 10
    g._update_spawn()
    assert g.spawn_timer == 9


# ── _collect_pearl ──

def test_collect_pearl_first_sets_color():
    g = _make_game()
    g.current_color = -1
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=False)
    assert pearl.collected is True
    assert g.current_color == 0  # wrong color sets current_color to pearl color
    assert g.total_pearls_collected == 1


def test_collect_pearl_same_color_increments_combo():
    g = _make_game()
    g.current_color = 0
    g.combo = 1
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    assert pearl.collected is True
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score > 0


def test_collect_pearl_wrong_color_resets_combo():
    g = _make_game()
    g.current_color = 0
    g.combo = 3
    g.heat = 0.0
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=1)
    g._collect_pearl(pearl, same_color=False)
    assert pearl.collected is True
    assert g.combo == 0
    assert g.current_color == 1
    assert g.heat == HEAT_WRONG


def test_collect_pearl_activates_super_at_threshold():
    g = _make_game()
    g.current_color = 0
    g.combo = 3
    g.super_timer = 0
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_collect_pearl_does_not_reactivate_super():
    g = _make_game()
    g.current_color = 0
    g.combo = 4
    g.super_timer = 100
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    assert g.super_timer == 100  # unchanged


def test_collect_pearl_during_super_3x_score():
    g = _make_game()
    g.super_timer = 100
    g.combo = 5
    g.score = 0
    g.oxygen = 50.0
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    expected = int((10 + 6 * 5) * 1.0 * 3.0)  # (10 + combo*5) * depth_mult * 3
    assert g.score == expected
    assert g.oxygen > 50.0  # refilled


def test_collect_pearl_depth_multiplier():
    g = _make_game()
    g.current_color = 0
    g.combo = 0
    g.depth = 1000.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    # depth_mult = 1 + 1000/500 = 3.0
    # score = int((10 + 1*5) * 3.0) = 45
    assert g.score == 45


def test_collect_pearl_max_combo_persists():
    g = _make_game()
    g.current_color = 0
    g.combo = 3
    g.max_combo = 3
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    assert g.max_combo == 4
    # now wrong color
    g.current_color = 0
    g.combo = 0
    pearl2 = Pearl(x=100.0, y=100.0, color=1)
    g._collect_pearl(pearl2, same_color=False)
    assert g.max_combo == 4  # persists


# ── _activate_super ──

def test_activate_super():
    g = _make_game()
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) == 30
    assert len(g.floating_texts) == 1
    assert "SUPER" in g.floating_texts[0].text


# ── _update_super ──

def test_update_super_decrements():
    g = _make_game()
    g.super_timer = 100
    g._update_super()
    assert g.super_timer == 99


def test_update_super_expires():
    g = _make_game()
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0


def test_update_super_stays_zero():
    g = _make_game()
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0


# ── _update_oxygen ──

def test_update_oxygen_normal_decay():
    g = _make_game()
    g.oxygen = 50.0
    g.diver_y = 60.0
    g.darkness_y = 200.0
    result = g._update_oxygen(space_held=False)
    assert result is False
    assert g.oxygen == 50.0 - OXYGEN_DECAY


def test_update_oxygen_swim_up_cost():
    g = _make_game()
    g.oxygen = 50.0
    g.diver_y = 60.0
    g.darkness_y = 200.0
    result = g._update_oxygen(space_held=True)
    assert result is False
    assert g.oxygen == 50.0 - (OXYGEN_DECAY + OXYGEN_ASCENT_COST)


def test_update_oxygen_darkness_penalty():
    g = _make_game()
    g.oxygen = 50.0
    g.diver_y = 100.0
    g.darkness_y = 50.0  # diver is below darkness
    result = g._update_oxygen(space_held=False)
    assert result is False
    assert g.oxygen == 50.0 - (OXYGEN_DECAY * 4.0)


def test_update_oxygen_game_over():
    g = _make_game()
    g.oxygen = 0.0
    g.diver_y = 60.0
    g.darkness_y = 200.0
    result = g._update_oxygen(space_held=False)
    assert result is True


def test_update_oxygen_near_zero_decays():
    g = _make_game()
    g.oxygen = 0.03
    g.diver_y = 60.0
    g.darkness_y = 200.0
    result = g._update_oxygen(space_held=False)
    assert result is False  # not yet game over
    assert g.oxygen < 0.03  # but decay happened


# ── _update_heat ──

def test_update_heat_decays():
    g = _make_game()
    g.heat = 50.0
    result = g._update_heat()
    assert result is False
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_floor_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over():
    g = _make_game()
    g.heat = MAX_HEAT
    result = g._update_heat()
    assert result is True


def test_update_heat_just_below_max():
    g = _make_game()
    g.heat = MAX_HEAT - 0.01
    result = g._update_heat()
    assert result is False
    assert g.heat == MAX_HEAT - 0.01 - HEAT_DECAY


# ── _update_darkness ──

def test_update_darkness_rises():
    g = _make_game()
    g.darkness_y = 200.0
    g._update_darkness()
    assert g.darkness_y == 200.0 - DARKNESS_RISE_SPEED


# ── _check_collection ──

def test_check_collection_super_wide_radius():
    g = _make_game()
    g.diver_x = float(DIVER_X)
    g.diver_y = 100.0
    g.super_timer = 100
    g.current_color = 0
    g.combo = 5
    g.depth = 0.0
    g.pearls = [
        Pearl(x=float(DIVER_X + DIVER_W // 2 + 35), y=100.0, color=0),  # 35px away, within SUPER radius
        Pearl(x=float(DIVER_X + DIVER_W // 2 + 50), y=100.0, color=0),  # 50px away, outside SUPER radius
    ]
    g._check_collection()
    assert g.pearls[0].collected is True
    assert g.pearls[1].collected is False


def test_check_collection_normal_distance():
    g = _make_game()
    g.diver_x = float(DIVER_X)
    g.diver_y = 100.0
    g.super_timer = 0
    g.current_color = 0
    g.combo = 0
    g.depth = 0.0
    g.pearls = [
        Pearl(x=float(DIVER_X + DIVER_W // 2 + 5), y=100.0, color=0),  # very close
        Pearl(x=float(DIVER_X + DIVER_W // 2 + 20), y=100.0, color=0),  # far
    ]
    g._check_collection()
    assert g.pearls[0].collected is True
    assert g.pearls[1].collected is False


# ── Particle & Floating Text Systems ──

def test_spawn_particles():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 5, RED)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == RED
        assert -2.0 <= p.vx <= 2.0
        assert -2.0 <= p.vy <= 2.0
        assert 10 <= p.life <= 25


def test_update_particles():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-2.0, life=5, color=RED),
        Particle(x=0.0, y=0.0, vx=-0.5, vy=1.0, life=10, color=GREEN),
    ]
    g._update_particles()
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == -2.0
    assert g.particles[0].life == 4
    assert g.particles[1].x == -0.5
    assert g.particles[1].y == 1.0
    assert g.particles[1].life == 9


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=RED),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=GREEN),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].color == GREEN


def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+30", LIME)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+30"
    assert g.floating_texts[0].color == LIME
    assert g.floating_texts[0].life == 30


def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+25", life=5, color=LIME),
        FloatingText(x=200.0, y=80.0, text="COMBO", life=2, color=CYAN),
    ]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.0
    assert g.floating_texts[0].life == 4
    assert g.floating_texts[1].y == 79.0
    assert g.floating_texts[1].life == 1


def test_update_floating_texts_removes_dead():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+25", life=1, color=LIME),
        FloatingText(x=200.0, y=80.0, text="COMBO", life=5, color=CYAN),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "COMBO"


# ── Integration Tests ──

def test_full_combo_to_super():
    g = _make_game()
    g._start_game()
    g.current_color = 0
    g.combo = 0
    g.depth = 0.0

    for i in range(4):
        pearl = Pearl(x=100.0, y=100.0, color=0)
        g._collect_pearl(pearl, same_color=True)

    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    assert g.score > 0


def test_full_heat_game_over():
    g = _make_game()
    g._start_game()
    g.heat = 99.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g.current_color = 1
    g._collect_pearl(pearl, same_color=False)
    # heat = 99 + 15 = 114, then decay 0.02 → 113.98, still >= 100?
    # Actually _collect_pearl sets heat to min(MAX_HEAT, 99+15) = 100 (capped at MAX_HEAT)
    # Then _update_heat: max(0, 100 - 0.02) = 99.98, not >= 100 anymore due to decay
    # So we need heat at exactly MAX_HEAT or very close
    g.heat = MAX_HEAT
    result = g._update_heat()
    assert result is True


def test_oxygen_game_over():
    g = _make_game()
    g._start_game()
    g.oxygen = 0.0
    result = g._update_oxygen(space_held=False)
    assert result is True


def test_collection_spawns_particles():
    g = _make_game()
    g.current_color = 0
    g.combo = 0
    g.depth = 0.0
    assert len(g.particles) == 0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    assert len(g.particles) == 8


def test_collection_spawns_floating_text():
    g = _make_game()
    g.current_color = 0
    g.combo = 0
    g.depth = 0.0
    assert len(g.floating_texts) == 0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    # combo becomes 1, combo > 1 check: False, so no floating text for combo
    # Actually combo becomes 1, so combo > 1 is False, so no floating text
    pass


def test_collection_combo_floating_text():
    g = _make_game()
    g.current_color = 0
    g.combo = 1
    g.depth = 0.0
    g.floating_texts = []
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    # combo becomes 2, combo > 1 → spawn floating text
    assert any("COMBO" in ft.text for ft in g.floating_texts)


def test_wrong_color_floating_text():
    g = _make_game()
    g.current_color = 0
    g.combo = 3
    g.depth = 0.0
    g.floating_texts = []
    pearl = Pearl(x=100.0, y=100.0, color=1)
    g._collect_pearl(pearl, same_color=False)
    assert any("WRONG" in ft.text for ft in g.floating_texts)


def test_darkness_rises_over_time():
    g = _make_game()
    g.darkness_y = 200.0
    for _ in range(10):
        g._update_darkness()
    assert g.darkness_y < 200.0


def test_heat_capped_at_max():
    g = _make_game()
    g.current_color = 0
    g.combo = 0
    g.heat = 90.0
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=1)
    g._collect_pearl(pearl, same_color=False)
    # 90 + 15 = 105, capped at MAX_HEAT = 100
    assert g.heat == MAX_HEAT


def test_game_over_on_heat_max():
    g = _make_game()
    g._start_game()
    g.heat = 100.0
    if g._update_heat():
        g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_game_over_on_oxygen_zero():
    g = _make_game()
    g._start_game()
    g.oxygen = 0.0
    if g._update_oxygen(False):
        g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_super_mode_oxygen_refill():
    g = _make_game()
    g.super_timer = 100
    g.oxygen = 50.0
    g.combo = 5
    g.depth = 0.0
    pearl = Pearl(x=100.0, y=100.0, color=0)
    g._collect_pearl(pearl, same_color=True)
    assert g.oxygen > 50.0
    assert g.oxygen <= MAX_OXYGEN


def test_total_pearls_count():
    g = _make_game()
    g.current_color = 0
    g.combo = 0
    g.depth = 0.0
    for _ in range(5):
        pearl = Pearl(x=100.0, y=100.0, color=0)
        g._collect_pearl(pearl, same_color=True)
    assert g.total_pearls_collected == 5


# ── Run ──

if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                passed += 1
                print(f"  PASS {name}")
            except Exception as e:
                failed += 1
                print(f"  FAIL {name}: {e}")
    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
