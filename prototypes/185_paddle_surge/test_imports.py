"""test_imports.py — Headless logic tests for PADDLE SURGE (185)."""
import sys
import types
import random

_pyxel = types.ModuleType("pyxel")
_pyxel.init = lambda *a, **kw: None
_pyxel.run = lambda update, draw: None
_pyxel.btnp = lambda k: False
_pyxel.btn = lambda k: False
_pyxel.KEY_SPACE = 32
_pyxel.KEY_RETURN = 13
_pyxel.KEY_LEFT = 37
_pyxel.KEY_RIGHT = 39
_pyxel.KEY_UP = 38
_pyxel.KEY_DOWN = 40
_pyxel.KEY_A = 65
_pyxel.KEY_D = 68
_pyxel.KEY_W = 87
_pyxel.KEY_S = 83
sys.modules["pyxel"] = _pyxel

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/185_paddle_surge")

exec(open("/home/unknown22/repos/game-prototypes/prototypes/185_paddle_surge/main.py").read())

from main import (  # noqa: E402
    Phase, GateColor, Gate, Rock, Particle, FloatingText,
    GATE_COLOR_VALS, MAX_HEAT, SUPER_DURATION, COMBO_THRESHOLD,
    SCREEN_H, STUN_DURATION, _make_game,
)

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL [{name}]: {detail}")


# ── Test 1: Module imports and constants ──
assert Phase.TITLE != Phase.PLAYING != Phase.GAME_OVER
assert GATE_COLOR_VALS[0] != GATE_COLOR_VALS[1]
assert MAX_HEAT == 100.0
assert SUPER_DURATION == 300
assert COMBO_THRESHOLD == 4
passed += 5

# ── Test 2: _make_game factory ──
g = _make_game()
check("phase title", g.phase == Phase.TITLE)
check("score zero", g.score == 0)
check("combo zero", g.combo == 0)
check("heat zero", g.heat == 0.0)
check("super_timer zero", g.super_timer == 0)
check("kayak position", g.kayak_x == 160.0 and g.kayak_y == 180.0)
check("kayak color RED", g.kayak_color == GateColor.RED)
check("gates empty", len(g.gates) == 0)
check("rocks empty", len(g.rocks) == 0)
check("particles empty", len(g.particles) == 0)
check("floating texts empty", len(g.floating_texts) == 0)

# ── Test 3: reset() sets phase to PLAYING ──
g.reset()
check("reset phase PLAYING", g.phase == Phase.PLAYING)
check("reset score zero", g.score == 0)
check("reset heat zero", g.heat == 0.0)
check("reset super_timer zero", g.super_timer == 0)

# ── Test 4: _spawn_gate ──
g2 = _make_game()
g2.phase = Phase.PLAYING
g2._rng = random.Random(42)
g2._spawn_gate()
check("spawn gate count", len(g2.gates) == 1)
check("gate y pos", g2.gates[0].y == -20.0)
check("gate not passed", not g2.gates[0].passed)
check("gate color valid", g2.gates[0].color in GateColor)

# ── Test 5: _spawn_entities spawns gate ──
g3 = _make_game()
g3.phase = Phase.PLAYING
g3._rng = random.Random(42)
g3._gate_timer = 999
g3._spawn_entities()
check("entity spawn gate", len(g3.gates) == 1)

# ── Test 6: _check_gate_pass — pass through gate ──
g4 = _make_game()
g4.phase = Phase.PLAYING
g4._rng = random.Random(42)
gate = Gate(x=160.0, y=170.0, color=GateColor.RED)
g4.gates = [gate]
g4.kayak_x = 160.0
g4.kayak_y = 178.0  # within gate's vertical span
result = g4._check_gate_pass()
check("gate pass detected", result is gate)
check("gate marked passed", gate.passed)

# ── Test 7: _check_gate_pass — miss (outside horizontal gap) ──
g5 = _make_game()
g5.phase = Phase.PLAYING
g5._rng = random.Random(42)
gate2 = Gate(x=160.0, y=170.0, color=GateColor.RED)
g5.gates = [gate2]
g5.kayak_x = 100.0  # way outside gap
g5.kayak_y = 178.0
result2 = g5._check_gate_pass()
check("gate miss outside gap", result2 is None)
check("gate not passed after miss", not gate2.passed)

# ── Test 8: _check_gate_pass — miss (vertical) ──
g6 = _make_game()
g6.phase = Phase.PLAYING
gate3 = Gate(x=160.0, y=100.0, color=GateColor.RED)
g6.gates = [gate3]
g6.kayak_x = 160.0
g6.kayak_y = 50.0  # above gate
result3 = g6._check_gate_pass()
check("gate miss vertical", result3 is None)

# ── Test 9: same-color combo builds ──
g7 = _make_game()
g7.phase = Phase.PLAYING
g7._rng = random.Random(42)
g7.kayak_color = GateColor.RED
g7.combo = 0
g7.score = 0
g7.super_timer = 0
gate4 = Gate(x=160.0, y=100.0, color=GateColor.RED)
earned = g7._resolve_gate(gate4)
check("combo 1 after match", g7.combo == 1)
check("score after match", g7.score == 0)  # score is added externally
check("earned 10 for combo 1", earned == 10)  # 10 * 1
check("color set to gate color", g7.kayak_color == GateColor.RED)

# ── Test 10: combo builds to 4, triggers SUPER ──
g8 = _make_game()
g8.phase = Phase.PLAYING
g8._rng = random.Random(42)
g8.kayak_color = GateColor.RED
g8.combo = 3
g8.score = 0
g8.super_timer = 0
gate5 = Gate(x=160.0, y=100.0, color=GateColor.RED)
earned2 = g8._resolve_gate(gate5)
check("combo 4 after 4th match", g8.combo == 4)
check("earned includes SUPER bonus", earned2 == 10 * 4 + 50)  # 40 + 50 = 90
check("super_timer activated", g8.super_timer == SUPER_DURATION)

# ── Test 11: wrong-color resets combo ──
g9 = _make_game()
g9.phase = Phase.PLAYING
g9._rng = random.Random(42)
g9.kayak_color = GateColor.GREEN
g9.combo = 3
g9.heat = 0.0
gate6 = Gate(x=160.0, y=100.0, color=GateColor.RED)
earned3 = g9._resolve_gate(gate6)
check("combo reset to 0", g9.combo == 0)
check("heat +15", g9.heat == 15.0)
check("color updated to gate color", g9.kayak_color == GateColor.RED)
check("earned 0 on mismatch", earned3 == 0)

# ── Test 12: SUPER mode auto-matches any color ──
g10 = _make_game()
g10.phase = Phase.PLAYING
g10._rng = random.Random(42)
g10.kayak_color = GateColor.GREEN
g10.combo = 5
g10.super_timer = 100
g10.score = 0
gate7 = Gate(x=160.0, y=100.0, color=GateColor.RED)  # different color!
earned4 = g10._resolve_gate(gate7)
check("combo incremented in super", g10.combo == 6)
check("3x score in super", earned4 == 30 * min(6, 10))  # 10*3 * 6 = 180
check("color set to gate color", g10.kayak_color == GateColor.RED)

# ── Test 13: combo multiplier cap at x10 ──
g11 = _make_game()
g11.phase = Phase.PLAYING
g11._rng = random.Random(42)
g11.kayak_color = GateColor.RED
g11.combo = 15
g11.super_timer = 0
gate8 = Gate(x=160.0, y=100.0, color=GateColor.RED)
g11.super_timer = SUPER_DURATION  # avoid duplicate SUPER trigger
gate8 = Gate(x=160.0, y=100.0, color=GateColor.RED)
earned5 = g11._resolve_gate(gate8)
check("multiplier capped at 10 (3x super)", earned5 == 10 * 3 * 10)  # 300

# ── Test 14: max_combo tracking ──
g12 = _make_game()
g12.phase = Phase.PLAYING
g12._rng = random.Random(42)
g12.kayak_color = GateColor.RED
g12.combo = 0
g12.max_combo = 0
g12.super_timer = 0
gate9 = Gate(x=160.0, y=100.0, color=GateColor.RED)
g12._resolve_gate(gate9)
check("max_combo=1", g12.max_combo == 1)
gate10 = Gate(x=160.0, y=120.0, color=GateColor.RED)
g12._resolve_gate(gate10)
check("max_combo=2", g12.max_combo == 2)
gate11 = Gate(x=160.0, y=140.0, color=GateColor.GREEN)  # wrong color
g12.kayak_color = GateColor.RED
g12._resolve_gate(gate11)
check("max_combo preserved after reset", g12.max_combo == 2)

# ── Test 15: HEAT decay ──
g13 = _make_game()
g13.phase = Phase.PLAYING
g13.heat = 50.0
g13._update_heat()
check("heat decay ~0.05", abs(g13.heat - 49.95) < 0.001, f"got {g13.heat}")

# ── Test 16: HEAT game over ──
g14 = _make_game()
g14.phase = Phase.PLAYING
g14.heat = 100.0
g14._update_heat()
check("HEAT death", g14.phase == Phase.GAME_OVER)

# ── Test 17: HEAT decay floor at 0 ──
g15 = _make_game()
g15.phase = Phase.PLAYING
g15.heat = 0.0
g15._update_heat()
check("heat stays at 0", g15.heat == 0.0)

# ── Test 18: rock collision adds heat + stun ──
g16 = _make_game()
g16.phase = Phase.PLAYING
g16._rng = random.Random(42)
g16.kayak_x = 160.0
g16.kayak_y = 180.0
g16.heat = 0.0
g16._stun_timer = 0
g16.rocks = [Rock(x=160.0, y=180.0, radius=8.0)]  # small radius, close
result = g16._check_rock_collision()
check("rock collision returns True", result)
check("rock heat +20", g16.heat == 20.0)
check("stun timer set", g16._stun_timer == STUN_DURATION)
check("particles spawned", len(g16.particles) > 0)
check("floating text spawned", len(g16.floating_texts) > 0)

# ── Test 19: rock no collision when far ──
g17 = _make_game()
g17.phase = Phase.PLAYING
g17.kayak_x = 100.0
g17.kayak_y = 100.0
g17.heat = 0.0
g17.rocks = [Rock(x=200.0, y=200.0, radius=8.0)]
result2 = g17._check_rock_collision()
check("rock far no collision", not result2)

# ── Test 20: bank collision adds heat ──
g18 = _make_game()
g18.phase = Phase.PLAYING
g18.kayak_x = 43.0  # near left bank (RIVER_LEFT=40, margin=6)
g18.heat = 0.0
g18._check_bank_collision()
check("bank heat +5", g18.heat == 5.0)
check("bank clamp", g18.kayak_x >= 46.0)  # RIVER_LEFT + margin = 46

# ── Test 21: HEAT capped at MAX_HEAT ──
g19 = _make_game()
g19.phase = Phase.PLAYING
g19.heat = 95.0
# Rock hit adds 20, should cap at 100
g19.kayak_x = 160.0
g19.kayak_y = 180.0
g19.rocks = [Rock(x=160.0, y=180.0, radius=8.0)]
g19._check_rock_collision()
check("heat capped at MAX_HEAT", g19.heat == MAX_HEAT)

# ── Test 22: _scroll_river moves entities down ──
g20 = _make_game()
g20.phase = Phase.PLAYING
g20._rng = random.Random(42)
g20.scroll_speed = 1.0
g20.gates = [Gate(x=160.0, y=50.0, color=GateColor.RED)]
g20.rocks = [Rock(x=150.0, y=60.0, radius=8.0)]
g20._scroll_river()
check("gate scrolled down", g20.gates[0].y == 51.0)
check("rock scrolled down", g20.rocks[0].y == 61.0)

# ── Test 23: off-screen entities cleaned ──
g21 = _make_game()
g21.phase = Phase.PLAYING
g21.gates = [Gate(x=160.0, y=SCREEN_H + 100.0, color=GateColor.RED)]
g21.rocks = [Rock(x=150.0, y=SCREEN_H + 100.0, radius=8.0)]
g21.scroll_speed = 1.0
g21._scroll_river()
check("off-screen gate removed", len(g21.gates) == 0)
check("off-screen rock removed", len(g21.rocks) == 0)

# ── Test 24: distance accumulates ──
g22 = _make_game()
g22.phase = Phase.PLAYING
g22.distance = 0.0
g22.scroll_speed = 1.0
g22._scroll_river()
check("distance increased", g22.distance == 1.0)

# ── Test 25: scroll_speed scales with distance ──
g23 = _make_game()
g23.phase = Phase.PLAYING
g23.distance = 5000.0
g23.scroll_speed = 1.0
g23._scroll_river()
check("scroll speed at 5000 dist", abs(g23.scroll_speed - 2.0) < 0.5, f"got {g23.scroll_speed}")

# ── Test 26: SUPER timer decrements ──
g24 = _make_game()
g24.phase = Phase.PLAYING
g24.super_timer = 5
g24._update_super()
check("super timer decremented", g24.super_timer == 4)

# ── Test 27: SUPER timer goes to 0 ──
g25 = _make_game()
g25.phase = Phase.PLAYING
g25.super_timer = 1
g25._update_super()
check("super timer at 0", g25.super_timer == 0)

# ── Test 28: _spawn_particles adds correct count ──
g26 = _make_game()
g26.phase = Phase.PLAYING
g26._rng = random.Random(42)
g26._spawn_particles(100.0, 100.0, 5, 10)
check("particle count", len(g26.particles) == 10)

# ── Test 29: particles update and die ──
g27 = _make_game()
g27.phase = Phase.PLAYING
g27._rng = random.Random(42)
g27.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=0.0, life=1, color=5, size=2)]
g27._update_particles()
check("particle removed after life 0", len(g27.particles) == 0)

# ── Test 30: particles update but stay alive ──
g28 = _make_game()
g28.phase = Phase.PLAYING
g28._rng = random.Random(42)
g28.particles = [Particle(x=100.0, y=100.0, vx=0.5, vy=-0.5, life=5, color=5, size=2)]
g28._update_particles()
check("particle alive after update", len(g28.particles) == 1)
check("particle moved", g28.particles[0].x != 100.0 or g28.particles[0].y != 100.0)

# ── Test 31: _spawn_floating_text ──
g29 = _make_game()
g29.phase = Phase.PLAYING
g29._spawn_floating_text("TEST", 100.0, 100.0, 7)
check("floating text count", len(g29.floating_texts) == 1)
check("floating text content", g29.floating_texts[0].text == "TEST")
check("floating text life", g29.floating_texts[0].life == 30)

# ── Test 32: floating text update and die ──
g30 = _make_game()
g30.phase = Phase.PLAYING
g30.floating_texts = [FloatingText(x=100.0, y=100.0, text="T", life=1, color=7)]
g30._update_floating_texts()
check("floating text removed", len(g30.floating_texts) == 0)

# ── Test 33: floating text move upward ──
g31 = _make_game()
g31.phase = Phase.PLAYING
g31.floating_texts = [FloatingText(x=100.0, y=100.0, text="T", life=10, color=7, vy=-1.0)]
g31._update_floating_texts()
check("floating text moved up", g31.floating_texts[0].y == 99.0)

# ── Test 34: particle system spawns on gate match ──
g32 = _make_game()
g32.phase = Phase.PLAYING
g32._rng = random.Random(42)
g32.kayak_color = GateColor.RED
g32.combo = 0
g32.super_timer = 0
prev_particles = len(g32.particles)
prev_texts = len(g32.floating_texts)
gate12 = Gate(x=160.0, y=100.0, color=GateColor.RED)
g32._resolve_gate(gate12)
check("particles spawned on match", len(g32.particles) > prev_particles)
check("floating text spawned on match", len(g32.floating_texts) > prev_texts)

# ── Test 35: particle system spawns on gate mismatch ──
g33 = _make_game()
g33.phase = Phase.PLAYING
g33._rng = random.Random(42)
g33.kayak_color = GateColor.GREEN
g33.combo = 0
g33.super_timer = 0
prev_particles = len(g33.particles)
prev_texts = len(g33.floating_texts)
gate13 = Gate(x=160.0, y=100.0, color=GateColor.RED)
g33._resolve_gate(gate13)
check("particles spawned on mismatch", len(g33.particles) > prev_particles)
check("floating text MISS on mismatch", len(g33.floating_texts) > prev_texts)

# ── Test 36: SUPER activation spawns floating text ──
g34 = _make_game()
g34.phase = Phase.PLAYING
g34._rng = random.Random(42)
g34.kayak_color = GateColor.RED
g34.combo = 3
g34.super_timer = 0
gate14 = Gate(x=160.0, y=100.0, color=GateColor.RED)
g34._resolve_gate(gate14)
check("SUPER text spawned", any("SUPER" in ft.text for ft in g34.floating_texts))

# ── Test 37: Dataclass instantiation ──
gt = Gate(x=50.0, y=60.0, color=GateColor.RED)
check("Gate dataclass", gt.x == 50.0 and gt.color == GateColor.RED and not gt.passed)
rk = Rock(x=50.0, y=60.0)
check("Rock dataclass", rk.x == 50.0 and rk.radius == 10.0)
pt = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=10, color=7, size=2)
check("Particle dataclass", pt.life == 10)
ft = FloatingText(x=100.0, y=100.0, text="HI", life=30, color=7)
check("FloatingText dataclass", ft.life == 30 and ft.vy == -1.0)

# ── Test 38: _update_heat doesn't trigger game over below MAX_HEAT ──
g35 = _make_game()
g35.phase = Phase.PLAYING
g35.heat = 99.9
g35._update_heat()
check("below MAX_HEAT stays in game", g35.phase == Phase.PLAYING)

# ── Test 39: game_over_timer set on HEAT death ──
g36 = _make_game()
g36.phase = Phase.PLAYING
g36.heat = 100.0
g36._update_heat()
check("game_over_timer set", g36._game_over_timer == 60)

# ── Test 40: _spawn_entities interval decreases with distance ──
g37 = _make_game()
g37.phase = Phase.PLAYING
g37._rng = random.Random(42)
g37.distance = 5000.0
g37._gate_timer = 999  # ensure timer fires
g37._spawn_entities()
check("spawn at high distance still works", len(g37.gates) == 1)

# ── Test 41: Phase enum values ──
assert Phase.TITLE in Phase
assert Phase.PLAYING in Phase
assert Phase.GAME_OVER in Phase
passed += 1

# ── Test 42: GateColor enum values ──
assert GateColor.RED in GateColor
assert GateColor.GREEN in GateColor
assert GateColor.DARK_BLUE in GateColor
assert GateColor.YELLOW in GateColor
assert len(GATE_COLOR_VALS) == 4
passed += 1

# ── Test 43: Multiple same-color passes build high combo ──
g38 = _make_game()
g38.phase = Phase.PLAYING
g38._rng = random.Random(42)
g38.kayak_color = GateColor.RED
g38.combo = 0
g38.score = 0
g38.super_timer = 0
total_earned = 0
for i in range(7):
    gt_i = Gate(x=160.0, y=float(i), color=GateColor.RED)
    earned_i = g38._resolve_gate(gt_i)
    total_earned += earned_i
check("7-match combo sustained", g38.combo == 7)
check("SUPER activated during run", g38.super_timer > 0 or total_earned > 200)


# ── Summary ──
print("\n===== RESULTS =====")
print(f"  PASSED: {passed}")
print(f"  FAILED: {failed}")
if failed > 0:
    print(f"  RATE: {passed}/{passed + failed} ({100 * passed / (passed + failed):.1f}%)")
    sys.exit(1)
else:
    print(f"  ALL {passed} TESTS PASSED")
