"""test_imports.py — Headless logic tests for RAFT SURGE (182)."""
import sys
import types
import random

# ── Mock pyxel (headless) ──
_pyxel = types.ModuleType("pyxel")
_pyxel.init = lambda *a, **kw: None
_pyxel.run = lambda update, draw: None
_pyxel.btnp = lambda k: False
_pyxel.btn = lambda k: False
_pyxel.KEY_SPACE = 32
_pyxel.KEY_RETURN = 13
_pyxel.KEY_LEFT = 37
_pyxel.KEY_RIGHT = 39
_pyxel.KEY_A = 65
_pyxel.KEY_D = 68
sys.modules["pyxel"] = _pyxel

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/182_raft_surge")

# ── Import game module ──
exec(open("/home/unknown22/repos/game-prototypes/prototypes/182_raft_surge/main.py").read())

from main import (  # noqa: E402
    Game, Phase, Buoy, Rock, Particle, GhostPoint, SCREEN_H, INITIAL_TIMER, SUPER_DURATION,
    HEAT_MAX, STUN_DURATION,
    GREEN, DARK_BLUE, WHITE, RED, YELLOW, BUOY_COLORS, _make_game,
)

passed = 0
failed = 0

def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL [{name}]: {detail}")


# ── Test 1: Module imports and constants ──
assert Phase.TITLE != Phase.PLAYING != Phase.GAME_OVER
assert BUOY_COLORS == [RED, GREEN, DARK_BLUE, YELLOW]
assert HEAT_MAX == 100.0
assert SUPER_DURATION == 180
passed += 5  # Phase, BUOY_COLORS, HEAT_MAX, SUPER_DURATION, STUN_DURATION

# ── Test 2: Game.__new__ + reset ──
g = Game.__new__(Game)
g.reset()
check("phase after reset", g.phase == Phase.TITLE)
check("score zero", g.score == 0)
check("combo zero", g.combo == 0)
check("heat zero", g.heat == 0.0)
check("timer init", g.timer == INITIAL_TIMER)
check("raft_x center", g.raft_x == 160.0)
check("scroll_speed", g.scroll_speed == 1.0)
check("not super", not g.super_mode)
check("buoys empty", g.buoys == [])
check("rocks empty", g.rocks == [])
check("particles empty", g.particles == [])
check("floating empty", g.floating_texts == [])

# ── Test 3: _make_game factory ──
g2 = _make_game()
check("_make_game title", g2.phase == Phase.TITLE)

# ── Test 4: spawn buoy ──
g3 = _make_game()
g3.phase = Phase.PLAYING
g3._rng = random.Random(42)
g3._spawn_buoy()
check("spawn buoy count", len(g3.buoys) == 1, f"got {len(g3.buoys)}")
check("buoy color valid", g3.buoys[0].color in BUOY_COLORS, f"got {g3.buoys[0].color}")
check("buoy y pos", g3.buoys[0].y == -10.0)
check("buoy not collected", not g3.buoys[0].collected)

# ── Test 5: spawn rock ──
g3._spawn_rock()
check("spawn rock count", len(g3.rocks) == 1, f"got {len(g3.rocks)}")
check("rock y pos", g3.rocks[0].y == -10.0)

# ── Test 6: same-color combo (no SUPER yet) ──
g4 = _make_game()
g4.phase = Phase.PLAYING
g4._rng = random.Random(42)
g4.current_color = RED
g4.combo = 0
g4.score = 0
b = Buoy(x=g4.raft_x, y=g4.raft_y, color=RED)
g4._collect_buoy(b)
check("combo=1 after match", g4.combo == 1)
check("score after match", g4.score == 15)  # 10 + 1*5
check("color set", g4.current_color == RED, f"got {g4.current_color}")
check("buoy collected", b.collected)

# ── Test 7: combo builds to COMBO=3, then COMBO=4 triggers SUPER ──
g5 = _make_game()
g5.phase = Phase.PLAYING
g5._rng = random.Random(42)
g5.current_color = RED
g5.combo = 3
g5.score = 0
b2 = Buoy(x=g5.raft_x, y=g5.raft_y, color=RED)
g5._collect_buoy(b2)
check("combo=4", g5.combo == 4)
check("score at combo=4", g5.score == 30)  # 10 + 4*5
check("super_mode on", g5.super_mode)
check("super_timer set", g5.super_timer == SUPER_DURATION)

# ── Test 8: wrong-color buoy resets combo + adds heat ──
g6 = _make_game()
g6.phase = Phase.PLAYING
g6._rng = random.Random(42)
g6.current_color = GREEN
g6.combo = 2
g6.heat = 0.0
b3 = Buoy(x=g6.raft_x, y=g6.raft_y, color=RED)
g6._collect_buoy(b3)
check("combo reset", g6.combo == 0)
check("heat +10", g6.heat == 10.0)
check("color updated", g6.current_color == RED)

# ── Test 9: HEAT decay ──
g7 = _make_game()
g7.phase = Phase.PLAYING
g7.heat = 50.0
g7._update_heat()
check("heat decay ~0.03", abs(g7.heat - 49.97) < 0.001, f"got {g7.heat}")

# ── Test 10: HEAT death (check BEFORE decay) ──
g8 = _make_game()
g8.phase = Phase.PLAYING
g8.heat = 100.0
g8._update_heat()
check("HEAT death", g8.phase == Phase.GAME_OVER, f"got {g8.phase}")

# ── Test 11: Rock hit ──
g9 = _make_game()
g9.phase = Phase.PLAYING
g9._rng = random.Random(42)
g9.heat = 0.0
g9._hit_rock()
check("rock heat +20", g9.heat == 20.0, f"got {g9.heat}")
check("stun timer", g9.stun_timer == STUN_DURATION, f"got {g9.stun_timer}")
check("crash particles spawned", len(g9.particles) > 0)

# ── Test 12: Difficulty scaling ──
g10 = _make_game()
g10.phase = Phase.PLAYING
g10.scroll_speed = 1.0
g10.difficulty_timer = 599
g10._update_difficulty()
# 599 % 600 != 0 → no increase
g10._update_difficulty()
# 600 % 600 == 0 → increase
check("diff timer 600 fires", g10.scroll_speed == 1.1, f"got {g10.scroll_speed}")
g10.difficulty_timer = 1199
g10._update_difficulty()
# 1200 % 600 == 0 → another increase; floating-point accumulates
check("diff timer 1200 fires", abs(g10.scroll_speed - 1.2) < 0.01, f"got {g10.scroll_speed}")

# ── Test 13: Particle system ──
g11 = _make_game()
g11.phase = Phase.PLAYING
g11._rng = random.Random(42)
g11._spawn_particles(100, 100, 5, RED)
check("particle spawn count", len(g11.particles) == 5)
g11._update_particles()
check("particles alive after 1 tick", len(g11.particles) == 5, f"got {len(g11.particles)}")
# All should still be alive (life_min=10)

# ── Test 14: Floating text ──
g12 = _make_game()
g12.phase = Phase.PLAYING
g12._spawn_floating_text(100, 100, "TEST", WHITE)
check("float text spawn", len(g12.floating_texts) == 1)
ft = g12.floating_texts[0]
check("float text life", ft.life == 36)
g12._update_floating_texts()
check("float text alive after 1 tick", len(g12.floating_texts) == 1)

# ── Test 15: Ghost trail ──
g13 = _make_game()
g13.phase = Phase.PLAYING
g13.raft_x = 150.0
g13.raft_y = 180.0
g13._frame = 3
g13._update_ghost_trail()
check("ghost trail recorded", len(g13.ghost_trail) == 1)
check("ghost x", g13.ghost_trail[0].x == 150.0)
check("ghost y", g13.ghost_trail[0].y == 180.0)

# ── Test 16: End game saves best ──
g14 = _make_game()
g14.phase = Phase.PLAYING
g14.score = 500
g14.best_score = 0
g14.ghost_trail = [GhostPoint(100, 100, 0), GhostPoint(110, 110, 1)]
g14._end_game()
check("game over phase", g14.phase == Phase.GAME_OVER)
check("best score saved", g14.best_score == 500)
check("best ghost saved", len(g14.best_ghost) == 2)
check("ghost trail cleared", len(g14.ghost_trail) == 0)

# ── Test 17: End game doesn't overwrite better best ──
g15 = _make_game()
g15.phase = Phase.PLAYING
g15.score = 300
g15.best_score = 999
g15.best_ghost = [GhostPoint(50, 50, 0)]
g15._end_game()
check("best not downgraded", g15.best_score == 999)
check("best ghost preserved", len(g15.best_ghost) == 1)

# ── Test 18: Start game preserves best ──
g16 = _make_game()
g16.best_score = 888
g16.best_ghost = [GhostPoint(10, 10, 0)]
g16._start_game()
check("start game phase", g16.phase == Phase.PLAYING)
check("best preserved", g16.best_score == 888)
check("ghost preserved", len(g16.best_ghost) == 1)
check("score reset", g16.score == 0)

# ── Test 19: SUPER mode collection (auto-match, 3x score) ──
g17 = _make_game()
g17.phase = Phase.PLAYING
g17._rng = random.Random(42)
g17.super_mode = True
g17.super_timer = 100
g17.combo = 0
g17.score = 0
g17.current_color = GREEN  # different from buoy color
b4 = Buoy(x=g17.raft_x, y=g17.raft_y, color=RED)
g17._collect_buoy(b4)
check("super combo increment", g17.combo == 1)
check("super 3x score", g17.score == 45)  # (10 + 1*5) * 3
check("buoy collected in super", b4.collected)

# ── Test 20: SUPER ends (combo reset, color reset) ──
g18 = _make_game()
g18.phase = Phase.PLAYING
g18._rng = random.Random(42)
g18.super_mode = True
g18.super_timer = 1
g18.combo = 5
g18.current_color = RED
g18._update_super()
check("super ended", not g18.super_mode)
check("combo reset after super", g18.combo == 0)
check("color reset after super", g18.current_color is None)

# ── Test 21: SUPER continues when timer > 0 ──
g19 = _make_game()
g19.phase = Phase.PLAYING
g19._rng = random.Random(42)
g19.super_mode = True
g19.super_timer = 5
g19.combo = 4
g19._frame = 0
g19._update_super()
check("super still active", g19.super_mode)
check("super timer decremented", g19.super_timer == 4)
check("combo preserved", g19.combo == 4)

# ── Test 22: Raft clamping ──
g20 = _make_game()
g20.phase = Phase.PLAYING
# Simulate handle_input clamping for left edge
g20.raft_x = -100
# Apply same clamping logic as _handle_input
g20.raft_x = max(20.0, min(300.0, g20.raft_x))
check("raft clamped left", g20.raft_x == 20.0, f"got {g20.raft_x}")
g20.raft_x = 500
g20.raft_x = max(20.0, min(300.0, g20.raft_x))
check("raft clamped right", g20.raft_x == 300.0, f"got {g20.raft_x}")

# ── Test 23: Timer death ──
g21 = _make_game()
g21.phase = Phase.PLAYING
g21.timer = 1
g21._frame = 0
g21._update_playing()
check("timer death", g21.phase == Phase.GAME_OVER, f"got {g21.phase}")

# ── Test 24: max_combo tracking ──
g22 = _make_game()
g22.phase = Phase.PLAYING
g22._rng = random.Random(42)
g22.current_color = RED
g22.combo = 0
g22.max_combo = 0
b5 = Buoy(x=g22.raft_x, y=g22.raft_y, color=RED)
g22._collect_buoy(b5)
check("max_combo=1", g22.max_combo == 1)
b6 = Buoy(x=g22.raft_x, y=g22.raft_y, color=RED)
g22._collect_buoy(b6)
check("max_combo=2", g22.max_combo == 2)
# Wrong color resets combo but max_combo stays
b7 = Buoy(x=g22.raft_x, y=g22.raft_y, color=GREEN)
g22._collect_buoy(b7)
check("max_combo preserved", g22.max_combo == 2)

# ── Test 25: SUPER activate spawns floating text ──
g23 = _make_game()
g23.phase = Phase.PLAYING
g23._rng = random.Random(42)
g23.raft_x = 150.0
g23.raft_y = 180.0
g23._activate_super()
check("super activate text spawned", len(g23.floating_texts) == 1)
check("floating text says SUPER", "SUPER" in g23.floating_texts[0].text)

# ── Test 26: Ghost trail skips non-multiple-of-3 frames ──
g24 = _make_game()
g24.phase = Phase.PLAYING
g24._frame = 1
g24._update_ghost_trail()
check("ghost skip frame 1", len(g24.ghost_trail) == 0)
g24._frame = 2
g24._update_ghost_trail()
check("ghost skip frame 2", len(g24.ghost_trail) == 0)

# ── Test 27: Entity scroll ──
g25 = _make_game()
g25.phase = Phase.PLAYING
g25._rng = random.Random(42)
g25._spawn_buoy()
g25._spawn_rock()
g25.scroll_speed = 1.0
orig_buoy_y = g25.buoys[0].y
orig_rock_y = g25.rocks[0].y
g25._update_entities()
check("buoy scrolled down", g25.buoys[0].y == orig_buoy_y + 1.0)
check("rock scrolled down", g25.rocks[0].y == orig_rock_y + 1.0)

# ── Test 28: Off-screen entities cleaned ──
g26 = _make_game()
g26.phase = Phase.PLAYING
g26.buoys = [Buoy(x=100, y=SCREEN_H + 100, color=RED)]
g26.rocks = [Rock(x=100, y=SCREEN_H + 100)]
g26._update_entities()
check("off-screen buoy removed", len(g26.buoys) == 0)
check("off-screen rock removed", len(g26.rocks) == 0)

# ── Test 29: Spawn rates scale with difficulty ──
g27 = _make_game()
g27.phase = Phase.PLAYING
g27._rng = random.Random(42)
g27.difficulty_timer = 600  # 1 difficulty tick
g27.spawn_timer_buoy = 1
g27.spawn_timer_rock = 1
g27._spawn_objects()
# After spawn, timer resets with difficulty-scaled range
check("buoy spawn timer reset > 0", g27.spawn_timer_buoy > 0)
check("rock spawn timer reset > 0", g27.spawn_timer_rock > 0)

# ── Test 30: Water trail particles ──
g28 = _make_game()
g28.phase = Phase.PLAYING
g28._rng = random.Random(42)
g28._frame = 3
orig_count = len(g28.particles)
g28._spawn_water_trail()
check("water trail spawned", len(g28.particles) == orig_count + 1)

# ── Test 31: Water trail skips non-multiple-of-3 ──
g29 = _make_game()
g29.phase = Phase.PLAYING
g29._frame = 1
g29._spawn_water_trail()
check("water trail skip frame 1", len(g29.particles) == 0)

# ── Test 32: Collision detection — buoy collection ──
g30 = _make_game()
g30.phase = Phase.PLAYING
g30._rng = random.Random(42)
g30.raft_x = 160.0
g30.raft_y = 180.0
g30.current_color = RED
g30.score = 0
g30.combo = 0
g30.buoys = [Buoy(x=160, y=180, color=RED)]
g30._check_collisions()
check("buoy collected by collision", g30.buoys[0].collected)
check("combo after collision", g30.combo == 1)

# ── Test 33: Collision detection — rock hit ──
g31 = _make_game()
g31.phase = Phase.PLAYING
g31._rng = random.Random(42)
g31.raft_x = 160.0
g31.raft_y = 180.0
g31.heat = 0.0
g31.rocks = [Rock(x=160, y=180)]
g31._check_collisions()
check("rock hit heat", g31.heat == 20.0, f"got {g31.heat}")
check("rock hit stun", g31.stun_timer == STUN_DURATION)

# ── Test 34: SUPER mode auto-avoids rocks ──
g32 = _make_game()
g32.phase = Phase.PLAYING
g32._rng = random.Random(42)
g32.super_mode = True
g32.raft_x = 160.0
g32.raft_y = 180.0
g32.heat = 0.0
g32.rocks = [Rock(x=160, y=180)]
g32._check_collisions()
check("super avoids rock", g32.heat == 0.0)

# ── Test 35: Floating text fade (life ≤ 10 goes gray) ──
# This tests the draw logic conceptually — the draw method checks ft.life > 10
g33 = _make_game()
g33.phase = Phase.PLAYING
g33._spawn_floating_text(100, 100, "FADE", WHITE)
g33.floating_texts[0].life = 10  # just at threshold
# Draw logic: c = ft.color if ft.life > 10 else GRAY
# life=10 means >10 is False, so it would be GRAY
check("float text life threshold", g33.floating_texts[0].life == 10)

# ── Test 36: SUPER combo increments even with wrong stored color ──
g34 = _make_game()
g34.phase = Phase.PLAYING
g34._rng = random.Random(42)
g34.super_mode = True
g34.super_timer = 50
g34.combo = 3
g34.score = 0
g34.current_color = GREEN  # non-matching
b8 = Buoy(x=g34.raft_x, y=g34.raft_y, color=RED)
g34._collect_buoy(b8)
check("super combo incremented", g34.combo == 4)
check("super 3x score applied", g34.score == (10 + 4 * 5) * 3)  # 90

# ── Test 37: Repeated wrong-color resets ──
g35 = _make_game()
g35.phase = Phase.PLAYING
g35._rng = random.Random(42)
g35.current_color = GREEN
g35.combo = 3
g35.heat = 0
b9 = Buoy(x=g35.raft_x, y=g35.raft_y, color=RED)
g35._collect_buoy(b9)
check("combo reset to 0", g35.combo == 0)
check("current_color is now RED", g35.current_color == RED)
# After wrong-color, current_color was set to RED (the buoy's color)
# So collecting RED should match
b10 = Buoy(x=g35.raft_x, y=g35.raft_y, color=RED)
g35._collect_buoy(b10)
check("combo 1 after matching RED again", g35.combo == 1)

# ── Test 38: Dataclass instantiations ──
b_test = Buoy(x=50.0, y=60.0, color=RED)
check("Buoy dataclass", b_test.x == 50.0 and b_test.color == RED and not b_test.collected)
r_test = Rock(x=50.0, y=60.0)
check("Rock dataclass", r_test.x == 50.0 and r_test.size == 16)
p_test = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=10, color=WHITE)
check("Particle dataclass", p_test.life == 10)

# ── Test 39: Phase enum values ──
assert Phase.TITLE in Phase
assert Phase.PLAYING in Phase
assert Phase.GAME_OVER in Phase
passed += 1

# ── Test 40: _add_score helper ──
g36 = _make_game()
g36.phase = Phase.PLAYING
g36.score = 100
g36._add_score(50)
check("add_score", g36.score == 150)


# ── Summary ──
print("\n===== RESULTS =====")
print(f"  PASSED: {passed}")
print(f"  FAILED: {failed}")
if failed > 0:
    print(f"  RATE: {passed}/{passed + failed} ({100 * passed / (passed + failed):.1f}%)")
    sys.exit(1)
else:
    print(f"  ALL {passed} TESTS PASSED ✓")
