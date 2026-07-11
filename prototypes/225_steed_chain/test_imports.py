"""test_imports.py — Headless logic tests for 225_steed_chain."""
import sys
import random
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/225_steed_chain")
from main import (
    Game, Phase, Hurdle, Particle, FloatingText,
    SCREEN_W, SCREEN_H, GROUND_Y, HORSE_X, HORSE_W, HORSE_H,
    COLOR_VALS, COLOR_NAMES, SUPER_DURATION, MAX_HEAT,
    GAME_DURATION, JUMP_VELOCITY, GRAVITY, MIN_SCROLL_SPEED,
    MAX_SCROLL_SPEED, COLOR_CYCLE_INTERVAL,
    STUMBLE_COOLDOWN, HURDLE_SPAWN_INTERVAL_INITIAL,
    HURDLE_SPAWN_INTERVAL_MIN,
)


def make_game() -> Game:
    """Create a Game for headless testing using Game.__new__."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() touches
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.scroll_speed = MIN_SCROLL_SPEED
    g.hurdles = []
    g.particles = []
    g.floating_texts = []
    g.horse_color = 0
    g.horse_y = float(GROUND_Y)
    g.horse_vy = 0.0
    g.is_jumping = False
    g.jump_frame = 0
    g.stumble_frame = 0
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.total_hurdles_cleared = 0
    g.heat = 0
    g.super_timer = 0
    g.timer = GAME_DURATION
    g.spawn_countdown = HURDLE_SPAWN_INTERVAL_INITIAL
    g.color_timer = 0
    g._run_positions = []
    g.reset()
    g._rng = random.Random(42)
    return g


# ─── Dataclass tests ───

def test_hurdle_creation():
    h = Hurdle(x=100.0, y=200.0, color=0, height=30, width=20)
    assert h.x == 100.0
    assert h.y == 200.0
    assert h.color == 0
    assert h.height == 30
    assert h.width == 20
    assert h.cleared is False


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-3.0, life=15, color=8)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_creation():
    ft = FloatingText(x=50.0, y=30.0, text="+10", life=25, color=8)
    assert ft.text == "+10"
    assert ft.life == 25
    assert ft.color == 8


# ─── Game state initialization ───

def test_game_reset():
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.super_timer == 0
    assert g.timer == GAME_DURATION
    assert g.horse_color == 0
    assert g.is_jumping is False
    assert g.stumble_frame == 0
    assert len(g.hurdles) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g._run_positions == []


# ─── Hurdle collision detection ───

def test_hurdle_overlaps_horse():
    g = make_game()
    h = Hurdle(x=HORSE_X + 10, y=GROUND_Y, color=0)
    assert g._hurdle_overlaps_horse(h) is True


def test_hurdle_not_overlap_left():
    g = make_game()
    h = Hurdle(x=HORSE_X - 50, y=GROUND_Y, color=0)
    assert g._hurdle_overlaps_horse(h) is False


def test_hurdle_not_overlap_right():
    g = make_game()
    h = Hurdle(x=HORSE_X + HORSE_W + 10, y=GROUND_Y, color=0)
    assert g._hurdle_overlaps_horse(h) is False


def test_hurdle_edge_overlap_left():
    g = make_game()
    h = Hurdle(x=HORSE_X - 25, y=GROUND_Y, color=0)
    # hurdle.x + width = 55 + 20 = 75, HORSE_X = 80, so no overlap
    assert g._hurdle_overlaps_horse(h) is False


def test_hurdle_edge_overlap_right():
    g = make_game()
    h = Hurdle(x=HORSE_X + HORSE_W - 5, y=GROUND_Y, color=0)
    # hurdle.x=107 < HORSE_X+HORSE_W=112 and hurdle.x+width=127 > 80 → True
    assert g._hurdle_overlaps_horse(h) is True


# ─── Jump physics ───

def test_jump_initiates():
    g = make_game()
    g.is_jumping = True
    g.jump_frame = 0
    g.horse_vy = JUMP_VELOCITY
    assert g.is_jumping is True
    assert g.horse_vy == -8.0


def test_jump_physics_rise():
    g = make_game()
    g.is_jumping = True
    g.horse_vy = JUMP_VELOCITY
    g._update_horse()
    assert g.horse_y < GROUND_Y  # above ground
    assert g.horse_vy > JUMP_VELOCITY  # gravity applied (less negative)


def test_jump_lands():
    g = make_game()
    g.is_jumping = True
    g.horse_y = GROUND_Y - 1
    g.horse_vy = 10.0  # falling fast
    g._update_horse()
    assert g.horse_y == GROUND_Y
    assert g.is_jumping is False
    assert g.horse_vy == 0.0


# ─── Color cycle ───

def test_color_cycle():
    g = make_game()
    assert g.horse_color == 0
    # Simulate color cycling
    g.color_timer = COLOR_CYCLE_INTERVAL - 1
    # In _update_playing: color_timer += 1 -> >= 90, cycles to 1
    g.color_timer += 1
    assert g.color_timer >= COLOR_CYCLE_INTERVAL
    g.color_timer = 0
    g.horse_color = (g.horse_color + 1) % 4
    assert g.horse_color == 1


def test_color_cycle_full_rotation():
    g = make_game()
    colors_seen = []
    for _ in range(4):
        colors_seen.append(g.horse_color)
        g.horse_color = (g.horse_color + 1) % 4
    assert colors_seen == [0, 1, 2, 3]
    assert g.horse_color == 0


# ─── Collision resolution: matched jump ───

def test_resolve_hurdle_matched():
    g = make_game()
    h = Hurdle(x=100.0, y=GROUND_Y, color=0)
    g.horse_color = 0  # match
    g._resolve_hurdle(h, matched=True)
    assert h.cleared is True
    assert g.combo == 1
    assert g.score == 10  # 10 * 1 (combo)
    assert g.total_hurdles_cleared == 1
    assert g.max_combo == 1


def test_resolve_hurdle_combo_builds():
    g = make_game()
    g.combo = 3
    g.score = 30
    g.horse_color = 0
    h = Hurdle(x=100.0, y=GROUND_Y, color=0)
    g._resolve_hurdle(h, matched=True)
    assert g.combo == 4
    assert g.score == 30 + 40  # 10 * 4
    assert g.max_combo == 4


def test_resolve_hurdle_triggers_super():
    g = make_game()
    g.combo = 3
    g.horse_color = 0
    g.super_timer = 0
    h = Hurdle(x=100.0, y=GROUND_Y, color=0)
    g._resolve_hurdle(h, matched=True)
    assert g.combo == 4
    assert g._is_super() is True
    assert g.super_timer == SUPER_DURATION


def test_resolve_hurdle_super_mode_score():
    g = make_game()
    g.super_timer = 100  # active super
    g.combo = 5
    g.score = 100
    h = Hurdle(x=100.0, y=GROUND_Y, color=1)
    g._resolve_hurdle(h, matched=True)
    # In super mode, combo increments + 10 * combo * 3
    assert g.combo == 6
    assert g.score == 100 + (10 * 6 * 3)  # 100 + 180 = 280
    assert h.cleared is True


# ─── Collision resolution: mismatched jump ───

def test_resolve_hurdle_mismatched():
    g = make_game()
    g.combo = 3
    g.heat = 10
    g.horse_color = 0
    h = Hurdle(x=100.0, y=GROUND_Y, color=1)  # mismatch
    g._resolve_hurdle(h, matched=False)
    assert h.cleared is True
    assert g.combo == 0
    assert g.heat == 25  # 10 + 15
    assert g.stumble_frame == STUMBLE_COOLDOWN
    assert g.score == 0  # no points for mismatch


# ─── Crash (didn't jump) ───

def test_crash():
    g = make_game()
    g.combo = 2
    g.heat = 20
    g.is_jumping = True
    g.horse_y = GROUND_Y - 40
    h = Hurdle(x=100.0, y=GROUND_Y, color=0)
    g._crash(h)
    assert h.cleared is True
    assert g.combo == 0
    assert g.heat == 45  # 20 + 25
    assert g.stumble_frame == STUMBLE_COOLDOWN
    assert g.is_jumping is False
    assert g.horse_y == GROUND_Y


def test_crash_not_jumping():
    g = make_game()
    g.combo = 1
    g.heat = 0
    g.is_jumping = False
    h = Hurdle(x=100.0, y=GROUND_Y, color=0)
    g._crash(h)
    assert g.heat == 25
    assert g.is_jumping is False


# ─── Heat cap ───

def test_heat_capped_at_max():
    g = make_game()
    g.heat = MAX_HEAT - 5
    g.horse_color = 0
    h = Hurdle(x=100.0, y=GROUND_Y, color=1)  # mismatch → +15
    g._resolve_hurdle(h, matched=False)
    assert g.heat == MAX_HEAT


def test_crash_heat_capped():
    g = make_game()
    g.heat = MAX_HEAT - 10
    h = Hurdle(x=100.0, y=GROUND_Y, color=0)
    g._crash(h)
    assert g.heat == MAX_HEAT


# ─── Spawn interval progression ───

def test_spawn_interval_initial():
    g = make_game()
    assert g._current_spawn_interval() == HURDLE_SPAWN_INTERVAL_INITIAL


def test_spawn_interval_at_midpoint():
    g = make_game()
    g.timer = GAME_DURATION // 2
    interval = g._current_spawn_interval()
    assert HURDLE_SPAWN_INTERVAL_MIN < interval < HURDLE_SPAWN_INTERVAL_INITIAL


def test_spawn_interval_at_end():
    g = make_game()
    g.timer = 1
    interval = g._current_spawn_interval()
    assert abs(interval - HURDLE_SPAWN_INTERVAL_MIN) <= 1


# ─── Particle system ───

def test_spawn_particles():
    g = make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 200, 8, count=5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert 12 <= p.life <= 22
        assert p.color == 8


def test_update_particles_life_decreases():
    g = make_game()
    g._spawn_particles(100, 200, 8, count=3)
    initial_lives = [p.life for p in g.particles]
    g._update_particles()
    for p, il in zip(g.particles, initial_lives):
        assert p.life == il - 1


def test_particles_removed_when_life_zero():
    g = make_game()
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, life=1, color=8))
    g._update_particles()
    assert len(g.particles) == 0


# ─── Floating text ───

def test_spawn_floating_text():
    g = make_game()
    assert len(g.floating_texts) == 0
    g._spawn_floating_text(100, 200, "TEST", 8, life=30)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].life == 30


def test_floating_text_life_decreases():
    g = make_game()
    g._spawn_floating_text(100, 200, "TEST", 8, life=30)
    g._update_floating_texts()
    assert g.floating_texts[0].life == 29


def test_floating_text_removed_when_life_zero():
    g = make_game()
    g.floating_texts.append(FloatingText(x=0, y=0, text="X", life=1, color=8))
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ─── Scroll speed progression ───

def _update_playing_core(g: Game) -> None:
    """Simulate _update_playing without pyxel.btn/btnp calls."""
    if g.timer > 0:
        g.timer -= 1
    if g.heat >= MAX_HEAT:
        return
    progress = g._progress_ratio()
    g.scroll_speed = MIN_SCROLL_SPEED + (MAX_SCROLL_SPEED - MIN_SCROLL_SPEED) * progress
    if g.stumble_frame > 0:
        g.stumble_frame -= 1
    if g.super_timer > 0:
        g.super_timer -= 1
    g.color_timer += 1
    if g.color_timer >= COLOR_CYCLE_INTERVAL:
        g.color_timer = 0
        g.horse_color = (g.horse_color + 1) % 4
    g._update_horse()
    g._update_hurdles()
    g._spawn_hurdles()
    g._update_particles()
    g._update_floating_texts()


def test_scroll_speed_initial():
    g = make_game()
    g.timer = GAME_DURATION
    _update_playing_core(g)  # simulate without pyxel input
    assert abs(g.scroll_speed - MIN_SCROLL_SPEED) < 0.01


def test_scroll_speed_increases():
    g = make_game()
    g.timer = GAME_DURATION // 2
    _update_playing_core(g)
    assert g.scroll_speed > MIN_SCROLL_SPEED


def test_scroll_speed_max():
    g = make_game()
    g.timer = 1
    _update_playing_core(g)
    assert abs(g.scroll_speed - MAX_SCROLL_SPEED) < 0.01


# ─── Heat and game end ───

def test_game_end_on_heat():
    g = make_game()
    g.heat = MAX_HEAT  # at threshold
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_game_end_on_timer():
    g = make_game()
    g.timer = 0
    g._end_game()
    assert g.phase == Phase.GAME_OVER


# ─── High score tracking ───

def test_best_score_tracking():
    from main import Game as GameCls
    old_best = GameCls._best_score
    try:
        GameCls._best_score = 0
        g = make_game()
        g.score = 500
        g.max_combo = 10
        g._run_positions = [(GROUND_Y, 0.0)]
        g._end_game()
        assert GameCls._best_score == 500
        assert GameCls._best_max_combo == 10
        assert len(GameCls._best_run) > 0
    finally:
        GameCls._best_score = old_best


def test_low_score_does_not_update_best():
    from main import Game as GameCls
    old_best = GameCls._best_score
    try:
        GameCls._best_score = 1000
        g = make_game()
        g.score = 500
        g._end_game()
        assert GameCls._best_score == 1000  # unchanged
    finally:
        GameCls._best_score = old_best


# ─── Stumble cooldown ───

def test_stumble_cooldown_decrements():
    g = make_game()
    g.stumble_frame = STUMBLE_COOLDOWN
    _update_playing_core(g)
    assert g.stumble_frame == STUMBLE_COOLDOWN - 1


# ─── Super timer ───

def test_super_timer_decrements():
    g = make_game()
    g.super_timer = 100
    _update_playing_core(g)
    assert g.super_timer == 99


def test_is_super_when_timer_positive():
    g = make_game()
    g.super_timer = 1
    assert g._is_super() is True


def test_is_not_super_when_timer_zero():
    g = make_game()
    g.super_timer = 0
    assert g._is_super() is False


# ─── Hurdle spawning ───

def test_spawn_hurdle():
    g = make_game()
    assert len(g.hurdles) == 0
    g._spawn_hurdle()
    assert len(g.hurdles) == 1
    h = g.hurdles[0]
    assert h.x == SCREEN_W + 20
    assert h.y == GROUND_Y
    assert 0 <= h.color <= 3
    assert 20 <= h.height <= 50


def test_hurdles_move_left():
    g = make_game()
    g.scroll_speed = 3.0
    g.hurdles.append(Hurdle(x=200.0, y=GROUND_Y, color=0))
    g._update_hurdles()
    assert g.hurdles[0].x == 197.0


def test_hurdles_removed_when_offscreen():
    g = make_game()
    g.scroll_speed = 10.0
    g.hurdles.append(Hurdle(x=-25.0, y=GROUND_Y, color=0))
    g._update_hurdles()
    assert len(g.hurdles) == 0  # -25 - 10 = -35 < -30, removed


# ─── Constants validation ───

def test_color_vals_count():
    assert len(COLOR_VALS) == 4
    assert len(COLOR_NAMES) == 4


def test_screen_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert GROUND_Y == 200


def test_super_duration():
    assert SUPER_DURATION == 300


def test_game_duration():
    assert GAME_DURATION == 60 * 60  # 3600 frames


# ─── Phase enum ───

def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


if __name__ == "__main__":
    # Run all tests
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
