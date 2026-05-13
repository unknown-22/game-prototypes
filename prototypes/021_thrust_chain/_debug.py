import sys, types
mock_pyxel = types.ModuleType('pyxel')
mock_pyxel.COLOR_BLACK = 0
mock_pyxel.COLOR_BROWN = 4
mock_pyxel.COLOR_WHITE = 7
mock_pyxel.COLOR_RED = 8
mock_pyxel.COLOR_ORANGE = 9
mock_pyxel.COLOR_YELLOW = 10
mock_pyxel.COLOR_GREEN = 3
mock_pyxel.COLOR_CYAN = 12
mock_pyxel.COLOR_GRAY = 13
mock_pyxel.COLOR_NAVY = 1
mock_pyxel.btn = lambda key: False
mock_pyxel.btnp = lambda key: False
mock_pyxel.mouse_wheel = 0
sys.modules['pyxel'] = mock_pyxel
sys.path.insert(0, '/home/unknown22/repos/game-prototypes/prototypes/021_thrust_chain')
import main

# Test ship base positions
s = main.Ship(x=128, y=50, angle=0)
bl_x, bl_y = s.base_left()
br_x, br_y = s.base_right()
print(f'base_left: ({bl_x}, {bl_y})')
print(f'base_right: ({br_x}, {br_y})')
print(f'bl_y > 48: {bl_y > 48}')
print(f'br_y > 48: {br_y > 48}')
print(f'bl_x < br_x: {bl_x < br_x}')

# Test game_new
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

g._spawn_pads(count=5)
print(f'\npads spawned: {len(g.pads)}')
for pad in g.pads:
    print(f'  pad x={pad.x}, color_idx={pad.color_idx}, value={pad.value}, active={pad.active}')
    assert pad.active is True
    assert 0 <= pad.color_idx < 4
    assert pad.value >= 10
    assert main.PAD_WIDTH <= pad.x <= main.WIDTH - main.PAD_WIDTH
print('game_new: ALL OK')

# Test refill_pads
g2 = object.__new__(main.Game)
g2.pads = []
g2._spawn_pads(count=3)
print(f'\nrefill: {len(g2.pads)} pads initially')
g2.pads[0].active = False
g2._refill_pads()
print(f'refill: {len(g2.pads)} pads after refill, all active={all(p.active for p in g2.pads)}')
assert all(p.active for p in g2.pads)
assert len(g2.pads) == main.PAD_COUNT
print('refill_pads: ALL OK')
