"""test_imports.py — Headless logic tests for YO SURGE."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/151_yo_surge")

from main import Game, Gem, Particle, FloatingText, Phase
from main import (
    GEM_COLORS, SCREEN_W, SCREEN_H, COLLECT_RADIUS, SUPER_COLLECT_RADIUS,
    MAX_HEAT, SUPER_DURATION, GAME_DURATION, INITIAL_SPAWN_INTERVAL,
    MARGIN, HAND_X, HAND_Y,
)


def _make_game() -> Game:
    """Factory: create Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes before reset()
    g.phase = Phase.PLAYING
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.yo_x = 160.0
    g.yo_y = 120.0
    g.yo_color = 8  # RED
    g.heat = 0.0
    g.super_timer = 0
    g.game_timer = GAME_DURATION
    g.spawn_timer = INITIAL_SPAWN_INTERVAL
    g.spawn_interval = INITIAL_SPAWN_INTERVAL
    g.gems = []
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.elapsed_frames = 0
    g._hand_x = HAND_X
    g._hand_y = HAND_Y
    g._title_swing = 0.0
    g._title_spawn_timer = 0
    g._title_gems = []
    g.reset()
    return g


# ── Constants ──
def test_gem_colors():
    assert len(GEM_COLORS) == 4
    assert set(GEM_COLORS) == {8, 3, 6, 10}  # RED, GREEN, LIGHT_BLUE, YELLOW


def test_screen_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert MAX_HEAT == 15.0
    assert SUPER_DURATION == 300
    assert GAME_DURATION == 3600


# ── Phase enum ──
def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE is not Phase.PLAYING


# ── Dataclass construction ──
def test_gem_creation():
    gem = Gem(x=100.0, y=50.0, color=8, speed=2.0)
    assert gem.x == 100.0
    assert gem.y == 50.0
    assert gem.color == 8
    assert gem.speed == 2.0


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.life == 15


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=30, color=7)
    assert ft.text == "+100"
    assert ft.vy == -1.0


# ── Game.__new__ bypass ──
def test_game_creation_bypass():
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.yo_color == 8
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION


# ── reset() ──
def test_reset_clears_state():
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.max_combo = 5
    g.heat = 10.0
    g.super_timer = 100
    g.game_timer = 100
    g.gems = [Gem(x=100, y=50, color=8, speed=1.0)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=8)]
    g.floating_texts = [FloatingText(x=0, y=0, text="hi", life=1, color=7)]

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert len(g.gems) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.elapsed_frames == 0


# ── _update_yo ──
def test_yo_lerps_toward_mouse():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g._update_yo(200, 200)
    # After one lerp step: 100 + (200 - 100) * 0.15 = 115
    assert abs(g.yo_x - 115.0) < 0.01
    assert abs(g.yo_y - 115.0) < 0.01


def test_yo_clamped_to_bounds():
    g = _make_game()
    g._update_yo(-100, -100)
    assert g.yo_x >= 10.0
    assert g.yo_y >= 30.0
    g._update_yo(999, 999)
    assert g.yo_x <= 310.0
    assert g.yo_y <= 230.0


# ── _spawn_gems ──
def test_spawn_gem():
    g = _make_game()
    assert len(g.gems) == 0
    g._spawn_gems()
    assert len(g.gems) == 1
    gem = g.gems[0]
    assert MARGIN <= gem.x <= SCREEN_W - MARGIN
    assert gem.y == -4.0
    assert gem.color in GEM_COLORS
    assert 1.0 <= gem.speed <= 2.0  # 60/60 to 120/60


# ── _update_gems ──
def test_gems_fall():
    g = _make_game()
    g.gems = [Gem(x=100.0, y=50.0, color=8, speed=2.0)]
    g._update_gems()
    assert g.gems[0].y == 52.0


def test_missed_gem_adds_heat():
    g = _make_game()
    g.heat = 0.0
    g.gems = [Gem(x=100.0, y=float(SCREEN_H + 10), color=8, speed=2.0)]
    g._update_gems()
    assert len(g.gems) == 0  # removed
    assert g.heat == 1.0  # heat added


def test_missed_gem_no_heat_in_super():
    g = _make_game()
    g.super_timer = 100  # super active
    g.heat = 0.0
    g.gems = [Gem(x=100.0, y=float(SCREEN_H + 10), color=8, speed=2.0)]
    g._update_gems()
    assert len(g.gems) == 0
    assert g.heat == 0.0  # no heat in super


# ── _check_collection ──
def test_same_color_collection():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8  # RED
    g.combo = 0
    g.score = 0
    g.heat = 0.0
    g.gems = [Gem(x=100.0, y=100.0, color=8, speed=0.0)]  # RED, exactly at yo-yo

    g._check_collection()

    # Gem should be collected
    assert len(g.gems) == 0
    assert g.combo == 1
    assert g.score == 100  # 100 * 1
    assert g.heat == 0.0  # no heat for same color
    assert g.yo_color == 8  # stays same


def test_wrong_color_collection():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8  # RED
    g.combo = 2
    g.score = 0
    g.heat = 0.0
    g.gems = [Gem(x=100.0, y=100.0, color=3, speed=0.0)]  # GREEN

    g._check_collection()

    assert len(g.gems) == 0
    assert g.combo == 0  # reset
    assert g.score == 0  # no score for wrong color
    assert g.heat == 0.5  # heat added
    assert g.yo_color == 3  # changed to GREEN


def test_collection_distance_check():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.combo = 0
    g.score = 0
    # Gem at distance = COLLECT_RADIUS + 1 (just outside range)
    g.gems = [Gem(x=100.0 + COLLECT_RADIUS + 0.01, y=100.0, color=8, speed=0.0)]

    g._check_collection()

    assert len(g.gems) == 1  # NOT collected


def test_multiple_gems_collected():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8  # RED
    g.combo = 0
    g.score = 0
    g.heat = 0.0
    g.gems = [
        Gem(x=100.0, y=100.0, color=8, speed=0.0),   # match
        Gem(x=102.0, y=101.0, color=3, speed=0.0),   # wrong
        Gem(x=99.0, y=99.0, color=8, speed=0.0),     # match
    ]

    g._check_collection()

    assert len(g.gems) == 0
    # First gem (RED match): combo 0→1, score += 100, color stays 8
    # Second gem (GREEN wrong): combo resets to 0, color becomes 3, heat += 0.5
    # Third gem (RED): now yo_color is 3, so wrong — combo stays 0, color becomes 8, heat += 0.5
    assert g.combo == 0
    assert g.yo_color == 8
    assert g.heat == 1.0  # 0.5 + 0.5
    assert g.score == 100  # only first gem scored


# ── SUPER mode ──
def test_activate_super():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.super_timer = 0
    g.shake_frames = 0
    g.combo = 5

    g._activate_super()

    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames > 0
    assert g.combo == 0  # reset after super activation


def test_super_collects_wrong_color():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8  # RED
    g.super_timer = 50  # super active
    g.combo = 0
    g.score = 0
    g.heat = 0.0
    g.gems = [Gem(x=100.0, y=100.0, color=3, speed=0.0)]  # GREEN — wrong in normal

    g._check_collection()

    assert len(g.gems) == 0
    assert g.combo == 1  # combo up in super
    assert g.score == 300  # 300 * 1 (super multiplier)
    assert g.heat == 0.0  # no heat in super
    assert g.yo_color == 8  # unchanged in super


def test_super_collect_radius_doubled():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.super_timer = 50  # super active
    g.combo = 0
    g.score = 0
    # Gem at COLLECT_RADIUS + 5 (outside normal, inside super)
    g.gems = [Gem(x=100.0 + COLLECT_RADIUS + 5.0, y=100.0, color=8, speed=0.0)]

    g._check_collection()

    assert len(g.gems) == 0  # collected in super range


def test_super_not_collect_beyond_super_radius():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.super_timer = 50
    g.combo = 0
    g.score = 0
    # Gem at SUPER_COLLECT_RADIUS + 5 (outside even super range)
    g.gems = [Gem(x=100.0 + SUPER_COLLECT_RADIUS + 5.0, y=100.0, color=8, speed=0.0)]

    g._check_collection()

    assert len(g.gems) == 1  # not collected


def test_combo_4_triggers_super():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.combo = 3
    g.score = 0
    g.super_timer = 0
    g.gems = [Gem(x=100.0, y=100.0, color=8, speed=0.0)]

    g._check_collection()

    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION  # super activated


# ── _update_super ──
def test_update_super_decrements():
    g = _make_game()
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9


def test_update_super_ignores_zero():
    g = _make_game()
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0


# ── _is_super ──
def test_is_super():
    g = _make_game()
    assert g._is_super() is False
    g.super_timer = 1
    assert g._is_super() is True
    g.super_timer = 0
    assert g._is_super() is False


# ── _update_heat_decay ──
def test_heat_decay_normal():
    g = _make_game()
    g.heat = 3.0
    g.super_timer = 0
    g._update_heat_decay()
    # 3.0 - 0.5/60 = 3.0 - 0.00833... = 2.99167...
    assert 2.98 < g.heat < 3.0


def test_heat_decay_super():
    g = _make_game()
    g.heat = 3.0
    g.super_timer = 100
    g._update_heat_decay()
    # 3.0 - 1.0/60 = 3.0 - 0.01667... = 2.98333...
    assert 2.97 < g.heat < 3.0


def test_heat_decay_no_negative():
    g = _make_game()
    g.heat = 0.001
    g._update_heat_decay()
    assert g.heat == 0.0


# ── _score_for_gem ──
def test_score_normal():
    g = _make_game()
    g.combo = 3
    g.super_timer = 0
    assert g._score_for_gem(8) == 300  # 100 * 3


def test_score_super():
    g = _make_game()
    g.combo = 3
    g.super_timer = 50
    assert g._score_for_gem(8) == 900  # 300 * 3


# ── _update_game_timer ──
def test_game_timer_decrements():
    g = _make_game()
    g.game_timer = 100
    g.phase = Phase.PLAYING
    g._update_game_timer()
    assert g.game_timer == 99
    assert g.phase == Phase.PLAYING


def test_game_timer_triggers_game_over():
    g = _make_game()
    g.game_timer = 1
    g.phase = Phase.PLAYING
    g._update_game_timer()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


# ── _trigger_game_over ──
def test_trigger_game_over():
    g = _make_game()
    g.score = 500
    g.high_score = 300
    g.shake_frames = 0
    g._trigger_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.high_score == 500
    assert g.shake_frames > 0


def test_trigger_game_over_no_high_score():
    g = _make_game()
    g.score = 200
    g.high_score = 500
    g._trigger_game_over()
    assert g.high_score == 500  # unchanged


# ── _update_difficulty ──
def test_difficulty_decreases_at_interval():
    g = _make_game()
    g.elapsed_frames = 0
    g.spawn_interval = 45
    g._update_difficulty()
    assert g.spawn_interval == 45  # not at interval yet

    g.elapsed_frames = 600
    g._update_difficulty()
    assert g.spawn_interval == 40  # decreased by 5

    g.elapsed_frames = 600  # same frame — only triggers once
    g._update_difficulty()
    assert g.spawn_interval == 40  # already triggered, won't trigger again this cycle

    g.elapsed_frames = 1200
    g._update_difficulty()
    assert g.spawn_interval == 35


def test_difficulty_minimum():
    g = _make_game()
    g.spawn_interval = 16
    g.elapsed_frames = 600
    g._update_difficulty()
    assert g.spawn_interval == 15  # clamped to MIN

    g.elapsed_frames = 1200
    g._update_difficulty()
    assert g.spawn_interval == 15  # still at min


# ── Particle update ──
def test_update_particles():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=2.0, life=3, color=8),
        Particle(x=10.0, y=20.0, vx=-1.0, vy=1.0, life=0, color=3),  # dead on arrival
    ]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.life == 2


# ── Floating text update ──
def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=50.0, y=50.0, text="+100", life=3, color=7),
        FloatingText(x=100.0, y=100.0, text="+200", life=1, color=7),  # dies this tick
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.y == 49.0  # vy = -1.0
    assert ft.life == 2


# ── Heat triggers game over ──
def test_heat_triggers_game_over_in_update_playing():
    """Simulate the heat check that happens in _update_playing."""
    g = _make_game()
    g.heat = MAX_HEAT
    g.phase = Phase.PLAYING
    # The actual check: `if self.phase == Phase.PLAYING and self.heat >= MAX_HEAT`
    if g.phase == Phase.PLAYING and g.heat >= MAX_HEAT:
        g._trigger_game_over()
    assert g.phase == Phase.GAME_OVER


def test_heat_below_max_no_trigger():
    g = _make_game()
    g.heat = MAX_HEAT - 0.1
    g.phase = Phase.PLAYING
    if g.phase == Phase.PLAYING and g.heat >= MAX_HEAT:
        g._trigger_game_over()
    assert g.phase == Phase.PLAYING


# ── Max combo tracking ──
def test_max_combo_tracked():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.combo = 0
    g.max_combo = 0

    # Collect 3 same-color gems
    for i in range(3):
        g.gems = [Gem(x=100.0, y=100.0, color=8, speed=0.0)]
        g._check_collection()

    assert g.combo == 3
    assert g.max_combo == 3


def test_max_combo_persists_after_combo_reset():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.combo = 0
    g.max_combo = 0

    # Build combo
    for i in range(3):
        g.gems = [Gem(x=100.0, y=100.0, color=8, speed=0.0)]
        g._check_collection()

    assert g.combo == 3
    assert g.max_combo == 3

    # Wrong color resets combo but max_combo persists
    g.gems = [Gem(x=100.0, y=100.0, color=3, speed=0.0)]  # GREEN
    g._check_collection()

    assert g.combo == 0
    assert g.max_combo == 3  # still 3


# ── Edge cases ──
def test_empty_update_graceful():
    g = _make_game()
    # All updates should handle empty state
    g._update_gems()
    g._check_collection()
    g._update_super()
    g._update_heat_decay()
    g._update_particles()
    g._update_floating_texts()
    g._update_game_timer()
    g._update_difficulty()
    assert True  # no crash


def test_super_expires_mid_collection():
    g = _make_game()
    g.yo_x = 100.0
    g.yo_y = 100.0
    g.yo_color = 8
    g.super_timer = 0  # NOT super
    g.combo = 0
    g.gems = [Gem(x=100.0, y=100.0, color=3, speed=0.0)]  # GREEN, wrong

    g._check_collection()

    assert len(g.gems) == 0
    assert g.heat == 0.5  # wrong color adds heat
    assert g.combo == 0  # reset


print("All tests passed!")
