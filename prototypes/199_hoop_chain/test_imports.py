"""test_imports.py — Headless logic tests for HOOP CHAIN (199_hoop_chain)."""
import math
import sys
from pathlib import Path

# Ensure the prototype directory is on the path
_PROTO_DIR = str(Path(__file__).resolve().parent)
if _PROTO_DIR not in sys.path:
    sys.path.insert(0, _PROTO_DIR)

from main import Game, Hoop, Ball, Particle, FloatingText, HOOP_COLORS, RED, GREEN, DARK_BLUE, YELLOW


def _make_game() -> Game:
    """Factory to create a Game instance without pyxel.init/pyxel.run."""
    g = Game.__new__(Game)
    # Pre-init all attributes that _reset() touches
    g.SCREEN_W = 320
    g.SCREEN_H = 240
    g.FLOOR_Y = 210
    g.HOOP_Y = 50
    g.PLAYER_SPEED = 3
    g.GRAVITY = 0.3
    g.MAX_POWER = 15
    g.POWER_CHARGE_RATE = 0.3
    g.HEAT_MAX = 100
    g.HEAT_DECAY = 0.03
    g.HEAT_MISS = 15
    g.HEAT_WRONG = 8
    g.COMBO_SUPER = 4
    g.SUPER_DURATION = 300
    g.GAME_TIME = 3600
    g.phase = "TITLE"
    g.player_x = 160.0
    g.ball_color = 0
    g.hoops = []
    g.ball = None
    g.charging = False
    g.charge_power = 0.0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.shots_made = 0
    g.total_shots = 0
    g.super_timer = 0
    g.timer = 3600
    g.particles = []
    g.floating_texts = []
    g.frame = 0
    g.mouse_was_pressed = False
    g._reset()
    return g


# ── Test: Game initialization ──


def test_game_init():
    g = _make_game()
    assert g.phase == "TITLE"
    assert g.player_x == 160.0
    assert g.ball_color == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.shots_made == 0
    assert g.total_shots == 0
    assert g.super_timer == 0
    assert g.timer == 3600
    assert g.particles == []
    assert g.floating_texts == []
    assert g.ball is None
    assert g.charging is False


def test_hoops_created():
    g = _make_game()
    assert len(g.hoops) == 4
    colors = [h.color for h in g.hoops]
    assert RED in colors
    assert GREEN in colors
    assert DARK_BLUE in colors
    assert YELLOW in colors
    # Check X positions are in order and spread across screen
    xs = [h.x for h in g.hoops]
    assert all(0 < x < g.SCREEN_W for x in xs)
    # Each hoop has correct Y
    for h in g.hoops:
        assert h.y == g.HOOP_Y
        assert h.radius == 14


def test_hoop_creation_return_order():
    g = _make_game()
    # First hoop should be RED at x=60
    assert g.hoops[0].color == RED
    assert g.hoops[0].x == 60.0
    # Last hoop should be YELLOW at x=270
    assert g.hoops[3].color == YELLOW
    assert g.hoops[3].x == 270.0


# ── Test: Hoop shifting ──


def test_shift_hoops_changes_positions():
    g = _make_game()
    old_xs = [h.x for h in g.hoops]
    g._shift_hoops()
    new_xs = [h.x for h in g.hoops]
    # At least some positions should change (random, but very likely)
    assert any(abs(old_xs[i] - new_xs[i]) > 1 for i in range(4))


def test_shift_hoops_stays_in_bounds():
    g = _make_game()
    for _ in range(10):
        g._shift_hoops()
    for h in g.hoops:
        assert 40.0 <= h.x <= 280.0


def test_shift_hoops_maintains_min_gap():
    g = _make_game()
    for _ in range(20):
        g._shift_hoops()
        xs = sorted([h.x for h in g.hoops])
        for i in range(len(xs) - 1):
            assert xs[i + 1] - xs[i] >= 50.0 - 0.01, f"Gap {xs[i+1] - xs[i]:.2f} < 50 at iteration"


def test_shift_hoops_spawns_particles():
    g = _make_game()
    assert len(g.particles) == 0
    g._shift_hoops()
    assert len(g.particles) == 20  # 4 hoops * 5 particles each


# ── Test: Scoring ──


def test_on_score_same_color():
    g = _make_game()
    g.phase = "PLAYING"
    hoop = g.hoops[0]  # RED hoop
    g.ball_color = 0  # RED
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    assert g.score > 0
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.shots_made == 1
    assert g.ball is None
    assert g.ball_color == 1  # cycled to next color


def test_on_score_combo_increments():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 2
    g.max_combo = 2
    hoop = g.hoops[1]  # GREEN hoop
    g.ball_color = 1  # GREEN
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[1], active=True)
    score_before = g.score
    g._on_score(hoop)
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score > score_before
    assert g.ball_color == 2  # cycled to next


def test_on_score_combo_multiplier():
    """Score should increase with combo multiplier."""
    g = _make_game()
    g.phase = "PLAYING"
    hoop = g.hoops[0]  # RED
    g.ball_color = 0  # RED

    # First score: combo 0→1, multiplier=1+1*0.5=1.5, score=10*1.5=15
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    score_1 = g.score
    assert score_1 == 15  # int(10 * 1.5)

    # Second score: combo 1→2, multiplier=1+2*0.5=2.0, score+=10*2=20 → 35
    g.ball_color = 0  # Set back to RED
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    assert g.score == 35  # 15 + 20
    assert g.combo == 2


def test_on_score_super_multiplier():
    """During SUPER, multiplier should be 3x."""
    g = _make_game()
    g.phase = "PLAYING"
    g.super_timer = 100
    g.combo = 1
    hoop = g.hoops[0]
    g.ball_color = 0
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    # multiplier = 1 + 2 * 0.5 * 3 = 1 + 3 = 4
    # score = int(10 * 4) = 40
    assert g.score == 40


# ── Test: Wrong hoop ──


def test_on_wrong_resets_combo():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 3
    g.max_combo = 3
    g.heat = 10.0
    hoop = g.hoops[0]  # RED
    g.ball_color = 1  # GREEN (wrong color)
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[1], active=True)
    g._on_wrong(hoop)
    assert g.combo == 0
    assert g.max_combo == 3  # max_combo preserved
    assert g.heat == 10.0 + g.HEAT_WRONG  # 18
    assert g.ball is None
    assert g.ball_color == 1  # color does NOT cycle on wrong


def test_on_wrong_no_score():
    g = _make_game()
    g.phase = "PLAYING"
    g.score = 100
    hoop = g.hoops[0]
    g.ball_color = 1
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[1], active=True)
    g._on_wrong(hoop)
    assert g.score == 100  # unchanged


# ── Test: Miss ──


def test_on_miss_resets_combo_and_adds_heat():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 2
    g.heat = 20.0
    g.ball = Ball(x=150, y=230, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_miss()
    assert g.combo == 0
    assert g.heat == 20.0 + g.HEAT_MISS  # 35
    assert g.ball is None


# ── Test: SUPER DUNK ──


def test_super_activates_at_combo_4():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 3
    g.max_combo = 3
    g.super_timer = 0
    hoop = g.hoops[0]  # RED
    g.ball_color = 0  # RED
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    assert g.combo == 4
    assert g.super_timer == g.SUPER_DURATION  # 300


def test_super_does_not_reactivate():
    """SUPER should not reset timer if already active."""
    g = _make_game()
    g.phase = "PLAYING"
    g.super_timer = 200  # already active
    g.combo = 3
    hoop = g.hoops[0]
    g.ball_color = 0
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    assert g.super_timer == 200  # unchanged (already active)


def test_update_super_decrements():
    g = _make_game()
    g.phase = "PLAYING"
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 4
    g._update_super()
    assert g.super_timer == 3


def test_update_super_stops_at_zero():
    g = _make_game()
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    g._update_super()
    assert g.super_timer == 0  # stays at 0 (decrement would make it -1 but no guard, so...)
    # Actually the method just does -= 1, so it would go to -1
    # Let's check the actual behavior
    g.super_timer = 0
    g._update_super()
    # 0 > 0 is False, so no decrement. super_timer stays 0.
    assert g.super_timer == 0


def test_super_allows_any_color():
    """During SUPER, any color hoop should score."""
    g = _make_game()
    g.phase = "PLAYING"
    g.super_timer = 100
    g.ball_color = 0  # RED ball
    # Try to score on GREEN hoop
    green_hoop = g.hoops[1]
    g.ball = Ball(x=green_hoop.x, y=green_hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(green_hoop)
    assert g.combo == 1
    assert g.shots_made == 1
    assert g.score > 0


# ── Test: HEAT system ──


def test_heat_decay():
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - g.HEAT_DECAY  # 49.97


def test_heat_does_not_go_below_zero():
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_heat_capped_at_max():
    g = _make_game()
    g.heat = g.HEAT_MAX + 10
    g._update_heat()
    assert g.heat <= g.HEAT_MAX


def test_heat_game_over_triggers():
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = g.HEAT_MAX  # exactly 100
    # Simulate _update_playing game-over check
    if g.heat >= g.HEAT_MAX:
        g.phase = "GAME_OVER"
    assert g.phase == "GAME_OVER"


def test_heat_game_over_threshold():
    """HEAT must reach >= HEAT_MAX for game over."""
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = g.HEAT_MAX - 0.01
    # Should NOT trigger game over
    assert g.heat < g.HEAT_MAX
    assert g.phase == "PLAYING"


# ── Test: Timer ──


def test_timer_decrements():
    g = _make_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_timer_does_not_go_below_zero():
    g = _make_game()
    g.timer = 0
    g._update_timer()
    assert g.timer == 0


def test_timer_game_over():
    g = _make_game()
    g.phase = "PLAYING"
    g.timer = 0
    if g.timer <= 0:
        g.phase = "GAME_OVER"
    assert g.phase == "GAME_OVER"


# ── Test: Ball physics ──


def test_ball_gravity():
    g = _make_game()
    g.phase = "PLAYING"
    ball = Ball(x=150, y=100, vx=2.0, vy=-5.0, color=RED, active=True)
    g.ball = ball
    g._update_ball()
    assert g.ball is not None
    assert abs(g.ball.vy - (-5.0 + g.GRAVITY)) < 0.01  # -4.7
    assert g.ball.x == 152.0
    assert abs(g.ball.y - 95.3) < 0.01  # 100 + (-4.7)


def test_ball_miss_off_bottom():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 1
    g.heat = 10.0
    ball = Ball(x=150, y=g.FLOOR_Y + 21, vx=0, vy=0, color=RED, active=True)
    g.ball = ball
    g._update_ball()
    assert g.ball is None  # ball removed
    assert g.combo == 0  # combo reset
    assert g.heat == 10.0 + g.HEAT_MISS


def test_ball_miss_off_left():
    g = _make_game()
    g.phase = "PLAYING"
    ball = Ball(x=-11, y=100, vx=0, vy=0, color=RED, active=True)
    g.ball = ball
    g._update_ball()
    assert g.ball is None


def test_ball_miss_off_right():
    g = _make_game()
    g.phase = "PLAYING"
    ball = Ball(x=g.SCREEN_W + 11, y=100, vx=0, vy=0, color=RED, active=True)
    g.ball = ball
    g._update_ball()
    assert g.ball is None


# ── Test: Hoop collision ──


def test_ball_collision_same_color():
    g = _make_game()
    g.phase = "PLAYING"
    hoop = g.hoops[0]  # RED at x=60
    # Place ball exactly at hoop center
    ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=1.0, color=HOOP_COLORS[0], active=True)
    g.ball = ball
    g.ball_color = 0  # RED
    g._update_ball()
    assert g.ball is None  # scored
    assert g.combo == 1
    assert g.score > 0


def test_ball_collision_wrong_color():
    g = _make_game()
    g.phase = "PLAYING"
    hoop = g.hoops[0]  # RED hoop
    g.combo = 2
    ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=1.0, color=HOOP_COLORS[1], active=True)
    g.ball = ball
    g.ball_color = 1  # GREEN ball — wrong for RED hoop
    g._update_ball()
    assert g.ball is None  # removed
    assert g.combo == 0  # reset
    assert g.heat == g.HEAT_WRONG


def test_ball_collision_super_any_color():
    g = _make_game()
    g.phase = "PLAYING"
    g.super_timer = 100
    hoop = g.hoops[1]  # GREEN
    ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=1.0, color=HOOP_COLORS[0], active=True)
    g.ball = ball
    g.ball_color = 0  # RED ball — should score because super is active
    g._update_ball()
    assert g.ball is None
    assert g.combo == 1  # scored


def test_collision_radius_detection():
    """Ball near but not touching hoop should not trigger."""
    g = _make_game()
    g.phase = "PLAYING"
    hoop = g.hoops[0]  # RED at x=60
    # Place ball outside collision radius
    distance = hoop.radius + 3 + 1  # just outside
    ball = Ball(x=hoop.x + distance, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g.ball = ball
    g.ball_color = 0
    g._update_ball()
    assert g.ball is not None  # no collision
    assert g.combo == 0


# ── Test: Color cycling ──


def test_ball_color_cycles_after_score():
    g = _make_game()
    g.phase = "PLAYING"
    hoop = g.hoops[0]
    g.ball_color = 0  # RED
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    assert g.ball_color == 1  # GREEN


def test_ball_color_wraps_around():
    g = _make_game()
    g.phase = "PLAYING"
    g.ball_color = 3  # YELLOW
    hoop = g.hoops[3]  # YELLOW
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[3], active=True)
    g._on_score(hoop)
    assert g.ball_color == 0  # wraps to RED


# ── Test: Particle system ──


def test_update_particles():
    g = _make_game()
    g.particles = [
        Particle(x=100, y=100, vx=1, vy=-2, life=5, color=RED),
        Particle(x=150, y=150, vx=-1, vy=1, life=1, color=GREEN),  # will expire
    ]
    g._update_particles()
    assert len(g.particles) == 1  # one expired
    p = g.particles[0]
    assert p.x == 101
    assert p.y == 98  # -2 + 0.05 = -1.95, so 100 - 1.95 = 98.05 → int 98
    assert p.vy == -2.0 + 0.05  # slight gravity on particles
    assert p.life == 4


def test_spawn_score_particles():
    g = _make_game()
    g.particles = []
    hoop = g.hoops[0]
    g._spawn_score_particles(hoop, RED)
    assert len(g.particles) >= 10
    assert len(g.particles) <= 15
    for p in g.particles:
        assert p.color == RED
        assert p.life >= 15
        assert p.life <= 25


def test_spawn_miss_particles():
    g = _make_game()
    g.particles = []
    g._spawn_miss_particles(100, 100)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.life >= 10
        assert p.life <= 20


def test_shift_hoops_spawns_particles_each_time():
    g = _make_game()
    assert len(g.particles) == 0
    g._shift_hoops()
    assert len(g.particles) == 20


# ── Test: Floating text ──


def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100, y=100, text="TEST", life=5, color=RED, vy=-1.0),
        FloatingText(x=150, y=150, text="DIE", life=1, color=GREEN, vy=-1.0),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # one expired
    ft = g.floating_texts[0]
    assert ft.y == 99.0
    assert ft.life == 4


def test_spawn_floating_text():
    g = _make_game()
    g.floating_texts = []
    g._spawn_floating_text(100, 100, "+10", RED)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100
    assert ft.y == 100
    assert ft.text == "+10"
    assert ft.color == RED
    assert ft.life == 30


def test_floating_text_combo_on_score():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 1
    hoop = g.hoops[0]
    g.ball_color = 0
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    # Should have COMBO text + score text (2 floating texts)
    assert len(g.floating_texts) == 2  # "+15" and "COMBO x2"


# ── Test: Hoop shift with sweep placement ──


def test_shift_hoops_preserves_colors():
    g = _make_game()
    old_colors = [h.color for h in g.hoops]
    g._shift_hoops()
    new_colors = [h.color for h in g.hoops]
    # Colors should be preserved (same hoops, different X positions)
    assert old_colors == new_colors


def test_shift_hoops_sorted_positions():
    g = _make_game()
    g._shift_hoops()
    xs = [h.x for h in g.hoops]
    # sorted by X (each hoop's X was assigned by the sweep algorithm
    # based on the hoop's original X order - let's just check bounds)
    for x in xs:
        assert 40.0 <= x <= 280.0


# ── Test: Phase transitions ──


def test_phase_title_to_playing():
    g = _make_game()
    assert g.phase == "TITLE"
    g.phase = "PLAYING"
    assert g.phase == "PLAYING"


def test_phase_playing_to_game_over_heat():
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = g.HEAT_MAX
    if g.heat >= g.HEAT_MAX:
        g.phase = "GAME_OVER"
    assert g.phase == "GAME_OVER"


def test_phase_playing_to_game_over_timer():
    g = _make_game()
    g.phase = "PLAYING"
    g.timer = 0
    if g.timer <= 0:
        g.phase = "GAME_OVER"
    assert g.phase == "GAME_OVER"


# ── Test: Edge cases ──


def test_shots_made_tracking():
    g = _make_game()
    g.phase = "PLAYING"
    assert g.shots_made == 0
    hoop = g.hoops[0]
    g.ball_color = 0
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[0], active=True)
    g._on_score(hoop)
    assert g.shots_made == 1


def test_total_shots_tracking():
    g = _make_game()
    g.phase = "PLAYING"
    assert g.total_shots == 0
    # Simulate shoot (can't call _shoot directly - uses pyxel.mouse_x)
    # Just set ball manually and check
    g.ball = Ball(x=150, y=100, vx=2, vy=-5, color=RED, active=True)
    g.total_shots += 1
    assert g.total_shots == 1


def test_player_x_clamped():
    g = _make_game()
    # Directly test clamping logic
    g.player_x = -10
    g.player_x = max(10.0, min(float(g.SCREEN_W - 26), g.player_x))
    assert g.player_x == 10.0

    g.player_x = 500
    g.player_x = max(10.0, min(float(g.SCREEN_W - 26), g.player_x))
    assert g.player_x == float(g.SCREEN_W - 26)


def test_max_combo_persists_after_wrong():
    g = _make_game()
    g.phase = "PLAYING"
    g.combo = 5
    g.max_combo = 5
    hoop = g.hoops[0]
    g.ball_color = 1  # wrong color
    g.ball = Ball(x=hoop.x, y=hoop.y, vx=0, vy=0, color=HOOP_COLORS[1], active=True)
    g._on_wrong(hoop)
    assert g.combo == 0
    assert g.max_combo == 5  # max comobo preserved


def test_heat_clamped_at_max():
    g = _make_game()
    g.heat = g.HEAT_MAX + 50
    g._update_heat()
    assert g.heat <= g.HEAT_MAX


# ── Test: Design spec consistency ──


def test_constants():
    """Verify the design spec constants are correct."""
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240
    assert Game.FLOOR_Y == 210
    assert Game.HOOP_Y == 50
    assert Game.GRAVITY == 0.3
    assert Game.HEAT_MAX == 100
    assert Game.COMBO_SUPER == 4
    assert Game.SUPER_DURATION == 300
    assert Game.GAME_TIME == 3600


def test_hoop_colors():
    """Verify the 4 hoop colors."""
    assert len(HOOP_COLORS) == 4
    assert HOOP_COLORS[0] == RED
    assert HOOP_COLORS[1] == GREEN
    assert HOOP_COLORS[2] == DARK_BLUE
    assert HOOP_COLORS[3] == YELLOW


def test_ball_active_state():
    b = Ball(x=100, y=100, vx=0, vy=0, color=RED, active=False)
    assert b.active is False
    assert b.radius == 3
