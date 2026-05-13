"""test_imports.py — Headless logic tests for THRUST CHAIN."""
import sys
import types

# Set up mock pyxel BEFORE importing main
mock_pyxel = types.ModuleType("pyxel")
mock_pyxel.COLOR_BLACK = 0
mock_pyxel.COLOR_NAVY = 1
mock_pyxel.COLOR_PURPLE = 2
mock_pyxel.COLOR_GREEN = 3
mock_pyxel.COLOR_BROWN = 4
mock_pyxel.COLOR_DARK_BLUE = 5
mock_pyxel.COLOR_LIGHT_BLUE = 6
mock_pyxel.COLOR_WHITE = 7
mock_pyxel.COLOR_RED = 8
mock_pyxel.COLOR_ORANGE = 9
mock_pyxel.COLOR_YELLOW = 10
mock_pyxel.COLOR_LIME = 11
mock_pyxel.COLOR_CYAN = 12
mock_pyxel.COLOR_GRAY = 13
mock_pyxel.COLOR_PINK = 14
mock_pyxel.COLOR_PEACH = 15
mock_pyxel.KEY_LEFT = 0
mock_pyxel.KEY_RIGHT = 1
mock_pyxel.KEY_UP = 2
mock_pyxel.KEY_DOWN = 3
mock_pyxel.KEY_Z = 4
mock_pyxel.KEY_X = 5
mock_pyxel.KEY_A = 6
mock_pyxel.KEY_D = 7
mock_pyxel.KEY_W = 8
mock_pyxel.KEY_R = 9
mock_pyxel.KEY_Q = 10
mock_pyxel.MOUSE_BUTTON_LEFT = 0
mock_pyxel.MOUSE_BUTTON_RIGHT = 1

# Mock pyxel functions that return values
mock_pyxel.btn = lambda key: False
mock_pyxel.btnp = lambda key: False
mock_pyxel.mouse_wheel = 0

sys.modules["pyxel"] = mock_pyxel

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/021_thrust_chain")
import main


# ── Test constants ──
def test_constants():
    assert main.GRAVITY > 0
    assert main.THRUST_POWER > 0
    assert main.MAX_FUEL == 100.0
    assert main.MAX_HP == 100
    assert len(main.COLORS) == 4
    assert len(main.COLOR_NAMES) == 4


# ── Test Phase enum ──
def test_phase():
    assert main.Phase.PLAYING is not None
    assert main.Phase.GAME_OVER is not None
    assert main.Phase.LAND_PAUSE is not None


# ── Test LandingPad ──
def test_landing_pad():
    pad = main.LandingPad(x=100, color_idx=0, value=15)
    assert pad.x == 100
    assert pad.color_idx == 0
    assert pad.value == 15
    assert pad.active is True
    assert pad.width == main.PAD_WIDTH
    assert abs(pad.left - (100 - main.PAD_WIDTH / 2)) < 0.01
    assert abs(pad.right - (100 + main.PAD_WIDTH / 2)) < 0.01
    assert pad.color == main.COLORS[0]

    pad2 = main.LandingPad(x=200, color_idx=2)
    assert pad2.color == main.COLORS[2]
    assert pad2.value == 10  # default


# ── Test Particle ──
def test_particle():
    p = main.Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8, max_life=20)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.max_life == 20


# ── Test FloatingText ──
def test_floating_text():
    ft = main.FloatingText(x=50.0, y=100.0, text="+10", life=30, color=12)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.vy == -0.8


# ── Test GhostPoint ──
def test_ghost_point():
    gp = main.GhostPoint(x=50.0, y=60.0, angle=45.0)
    assert gp.x == 50.0
    assert gp.y == 60.0
    assert gp.angle == 45.0


# ── Test Ship ──
def test_ship_init():
    s = main.Ship(x=128, y=50)
    assert s.x == 128
    assert s.y == 50
    assert s.vx == 0.0
    assert s.vy == 0.0
    assert s.angle == 0.0
    assert s.color_idx == 0
    assert s.fuel == main.MAX_FUEL
    assert s.hp == main.MAX_HP
    assert s.thrusting is False


def test_ship_reset():
    s = main.Ship(x=50, y=30)
    s.vx = 5.0
    s.vy = 3.0
    s.fuel = 20
    s.hp = 50
    s.thrusting = True
    s.reset(128, 50)
    assert s.x == 128
    assert s.y == 50
    assert s.vx == 0.0
    assert s.vy == 0.0
    assert s.angle == 0.0
    assert s.fuel == main.MAX_FUEL
    assert s.hp == main.MAX_HP
    assert s.thrusting is False


def test_ship_nose_position():
    s = main.Ship(x=128, y=50, angle=0)
    nx, ny = s.nose_x(), s.nose_y()
    assert abs(nx - 128) < 0.01
    assert ny < 50  # nose is above center when angle=0


def test_ship_base_positions():
    s = main.Ship(x=128, y=50, angle=0)
    bl_x, bl_y = s.base_left()
    br_x, br_y = s.base_right()
    # Base should be below center
    assert bl_y > 50 - 2
    assert br_y > 50 - 2
    # Left base should be left of right base
    assert bl_x < br_x


def test_ship_color_property():
    s = main.Ship(x=100, y=50, color_idx=2)
    assert s.color == main.COLORS[2]


# ── Test LandingPad collision boundaries ──
def test_pad_collision():
    pad = main.LandingPad(x=128, width=40)
    # Center of ship over pad
    assert pad.left <= 128 <= pad.right
    # Edge cases
    assert pad.left < 128 < pad.right


# ── Test COLORS length matches COLOR_NAMES ──
def test_color_arrays():
    assert len(main.COLORS) == len(main.COLOR_NAMES)


# ── Test that Game class methods exist ──
def test_game_methods_exist():
    assert hasattr(main.Game, "reset_game")
    assert hasattr(main.Game, "_spawn_pads")
    assert hasattr(main.Game, "_update_physics")
    assert hasattr(main.Game, "_update_collision")
    assert hasattr(main.Game, "_on_safe_landing")
    assert hasattr(main.Game, "_on_crash_landing")
    assert hasattr(main.Game, "_on_game_over")


# ── Test Game initialization (headless) ──
def test_game_new():
    """Test Game.__new__ without calling __init__ (avoids pyxel.init)."""
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=main.WIDTH / 2, y=60)
    g.pads = []
    g.particles = []
    g.floating_texts = []
    g.ghost_trail = []
    g.player_trail = []
    g.phase = main.Phase.PLAYING
    g.land_timer = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_score = 0
    g.screen_shake = 0

    g._spawn_pads(count=4)
    assert len(g.pads) == 4
    for pad in g.pads:
        assert pad.active is True
        assert 0 <= pad.color_idx < 4
        assert pad.value >= 10
        assert main.PAD_WIDTH <= pad.x <= main.WIDTH - main.PAD_WIDTH


def test_spawn_pads_no_overlap():
    g = object.__new__(main.Game)
    g.pads = []
    g._spawn_pads(count=3)
    assert len(g.pads) == 3
    # Check pads don't overlap
    for i, p1 in enumerate(g.pads):
        for j, p2 in enumerate(g.pads):
            if i < j:
                assert abs(p1.x - p2.x) >= main.PAD_WIDTH + main.PAD_MIN_GAP - 1


def test_refill_pads():
    g = object.__new__(main.Game)
    g.pads = []
    g._spawn_pads(count=3)
    assert len(g.pads) == 3
    g.pads[0].active = False
    g._refill_pads()
    assert all(p.active for p in g.pads)
    assert len(g.pads) == main.PAD_COUNT


def test_safe_landing_same_color():
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=128, y=main.PAD_Y - 10)
    g.particles = []
    g.floating_texts = []
    g.pads = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.screen_shake = 0
    g.best_score = 0

    g.ship.color_idx = 0
    g.ship.vy = 0.5
    g.ship.vx = 0.1
    g.ship.angle = 0.0
    g.ship.fuel = 30
    g.ship.hp = 100

    pad = main.LandingPad(x=128, color_idx=0, value=20)
    g._on_safe_landing(pad)

    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 20  # 20 * 1
    assert g.ship.fuel > 30
    assert g.ship.hp == 100
    assert g.screen_shake == 3


def test_safe_landing_wrong_color():
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=128, y=main.PAD_Y - 10)
    g.particles = []
    g.floating_texts = []
    g.pads = []
    g.score = 50
    g.combo = 3
    g.max_combo = 3
    g.screen_shake = 0
    g.best_score = 0

    g.ship.color_idx = 0
    g.ship.vy = 0.3
    g.ship.vx = 0.0
    g.ship.angle = 0.0
    g.ship.fuel = 40
    g.ship.hp = 80

    pad = main.LandingPad(x=128, color_idx=1, value=15)
    g._on_safe_landing(pad)

    assert g.combo == 0
    assert g.score == 50
    assert g.ship.hp == 60  # -20 wrong color


def test_crash_landing():
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=128, y=main.PAD_Y - 10)
    g.particles = []
    g.floating_texts = []
    g.pads = []
    g.score = 10
    g.combo = 2
    g.max_combo = 2
    g.screen_shake = 0
    g.best_score = 0

    g.ship.hp = 80

    pad = main.LandingPad(x=128, color_idx=0, value=10)
    g._on_crash_landing(pad)

    assert g.combo == 0
    assert g.ship.hp == 50  # -30 crash


def test_game_over_transition():
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=128, y=50)
    g.particles = []
    g.floating_texts = []
    g.pads = []
    g.phase = main.Phase.PLAYING
    g.score = 100
    g.best_score = 50
    g.combo = 0
    g.player_trail = []

    g._on_game_over()

    assert g.phase == main.Phase.GAME_OVER
    assert g.best_score == 100
    assert g.screen_shake == 12


def test_update_physics_no_thrust():
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=128, y=50, vx=2.0, vy=0.0)
    g.particles = []

    g.ship.thrusting = False
    g._update_physics()

    assert g.ship.vy > 0  # gravity
    assert g.ship.vx < 2.0  # damping


def test_update_physics_with_thrust():
    g = object.__new__(main.Game)
    g.ship = main.Ship(x=128, y=50, vx=0.0, vy=0.0, angle=0, fuel=50)
    g.particles = []

    g.ship.thrusting = True
    g._update_physics()

    # Thrust at angle 0 should push upward
    assert g.ship.vy < 0.05
    assert g.ship.fuel < 50


def test_particle_update():
    g = object.__new__(main.Game)
    g.particles = [
        main.Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=1, color=8, max_life=20),
        main.Particle(x=30.0, y=40.0, vx=0.0, vy=0.0, life=5, color=3, max_life=10),
    ]

    g._update_particles()

    # life=1 becomes 0; should be filtered out
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_floating_text_update():
    g = object.__new__(main.Game)
    g.floating_texts = [
        main.FloatingText(x=50.0, y=100.0, text="HI", life=1, color=8),
        main.FloatingText(x=60.0, y=110.0, text="OK", life=10, color=3),
    ]

    g._update_floating_texts()

    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "OK"
    assert g.floating_texts[0].life == 9


def test_spawn_burst_particle():
    g = object.__new__(main.Game)
    g.particles = []
    g._spawn_burst_particle(100, 200, 8)
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 100
    assert p.y == 200
    assert p.life > 0


def test_add_floating_text():
    g = object.__new__(main.Game)
    g.floating_texts = []
    g._add_floating_text(50, 60, "+10", 3)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+10"
    assert g.floating_texts[0].life == 40
    assert g.floating_texts[0].color == 3


# ── Run all tests ──
if __name__ == "__main__":
    tests = [
        test_constants,
        test_phase,
        test_landing_pad,
        test_particle,
        test_floating_text,
        test_ghost_point,
        test_ship_init,
        test_ship_reset,
        test_ship_nose_position,
        test_ship_base_positions,
        test_ship_color_property,
        test_pad_collision,
        test_color_arrays,
        test_game_methods_exist,
        test_game_new,
        test_spawn_pads_no_overlap,
        test_refill_pads,
        test_safe_landing_same_color,
        test_safe_landing_wrong_color,
        test_crash_landing,
        test_game_over_transition,
        test_update_physics_no_thrust,
        test_update_physics_with_thrust,
        test_particle_update,
        test_floating_text_update,
        test_spawn_burst_particle,
        test_add_floating_text,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {test.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
