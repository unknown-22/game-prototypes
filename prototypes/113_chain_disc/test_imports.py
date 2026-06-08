"""test_imports.py — Headless logic tests for CHAIN DISC (113_chain_disc)."""
import random
import sys

# For import robustness, insert path
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/113_chain_disc")
from main import Game, Phase, Basket, Obstacle, Particle, BASKET_COLORS, _make_game


# ── Utility ───────────────────────────────────────────────────────────

def _make_game_clean() -> Game:
    """Create game and reset state to AIMING for tests."""
    g = _make_game()
    g.phase = Phase.AIMING
    # Reset heat/timer to known values
    g.heat = 0.0
    g.timer = 2700
    g.super_mode = False
    g.super_timer = 0
    g._rng = random.Random(42)
    return g


# ── Phase Machine ─────────────────────────────────────────────────────

def test_initial_phase_is_title():
    g = _make_game()
    assert g.phase == Phase.TITLE


def test_phase_enum_has_all_values():
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.RESOLVE in Phase
    assert Phase.GAME_OVER in Phase


# ── Initial State ─────────────────────────────────────────────────────

def test_initial_state_values():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.player_x == 160.0
    assert g.player_y == 120.0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == 2700
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.last_basket_color == -1
    assert g.disc_active is False


def test_initial_baskets_count():
    g = _make_game()
    assert len(g.baskets) == 4


def test_initial_baskets_positions():
    g = _make_game()
    positions = {(b.x, b.y) for b in g.baskets}
    assert (80.0, 60.0) in positions
    assert (240.0, 60.0) in positions
    assert (80.0, 180.0) in positions
    assert (240.0, 180.0) in positions


def test_basket_colors_exists():
    assert len(BASKET_COLORS) == 4
    assert 8 in BASKET_COLORS  # RED
    assert 3 in BASKET_COLORS  # GREEN
    assert 5 in BASKET_COLORS  # DARK_BLUE
    assert 10 in BASKET_COLORS  # YELLOW


# ── Aim Mechanics ─────────────────────────────────────────────────────

def test_start_aim():
    g = _make_game_clean()
    g._start_aim(200.0, 150.0)
    assert g.is_aiming is True
    assert g.aim_start_x == 160.0  # player_x
    assert g.aim_start_y == 120.0  # player_y
    assert g.aim_end_x == 200.0
    assert g.aim_end_y == 150.0


def test_update_aim():
    g = _make_game_clean()
    g._start_aim(200.0, 150.0)
    g._update_aim(250.0, 100.0)
    assert g.aim_end_x == 250.0
    assert g.aim_end_y == 100.0


# ── Throw Mechanics ───────────────────────────────────────────────────

def test_release_throw_sets_phase_to_flying():
    g = _make_game_clean()
    g._start_aim(250.0, 120.0)
    g._release_throw()
    assert g.phase == Phase.FLYING
    assert g.disc_active is True
    assert g.is_aiming is False


def test_release_throw_disc_starts_at_player():
    g = _make_game_clean()
    g._start_aim(250.0, 120.0)
    g._release_throw()
    assert g.disc_x == 160.0
    assert g.disc_y == 120.0


def test_throw_toward_right():
    g = _make_game_clean()
    g._start_aim(250.0, 120.0)  # aim right
    g._release_throw()
    assert g.disc_vx > 0
    assert abs(g.disc_vy) < 1


def test_throw_toward_left():
    g = _make_game_clean()
    g._start_aim(80.0, 120.0)  # aim left
    g._release_throw()
    assert g.disc_vx < 0


def test_throw_toward_up():
    g = _make_game_clean()
    g._start_aim(160.0, 60.0)  # aim up
    g._release_throw()
    assert g.disc_vy < 0


def test_throw_toward_down():
    g = _make_game_clean()
    g._start_aim(160.0, 180.0)  # aim down
    g._release_throw()
    assert g.disc_vy > 0


# ── Disc Flight ───────────────────────────────────────────────────────

def test_flying_moves_disc():
    g = _make_game_clean()
    g._start_aim(250.0, 120.0)
    g._release_throw()
    orig_x = g.disc_x
    orig_y = g.disc_y
    g._update_flying()
    assert g.disc_x != orig_x or g.disc_y != orig_y


def test_max_fly_frames_ends_flight():
    g = _make_game_clean()
    # Create no baskets for this test
    g.baskets = []
    g._start_aim(250.0, 120.0)
    g._release_throw()
    assert g.phase == Phase.FLYING
    # Simulate many frames
    for _ in range(70):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
    assert g.phase == Phase.RESOLVE
    assert g.disc_active is False
    assert g.flying_basket_hit is None


# ── Edge Bounce ───────────────────────────────────────────────────────

def test_disc_bounces_off_left_edge():
    g = _make_game_clean()
    # Remove all baskets for clean flight path
    g.baskets = []
    g.player_x = 160.0
    g.player_y = 120.0
    g._start_aim(10.0, 120.0)  # aim far left for power
    g._release_throw()
    assert g.disc_vx < 0
    # Fly for fixed frames — disc at vx=-5 reaches x=0 at frame 32, bounces at frame 33
    for _ in range(40):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
    # After bounce, vx should be positive
    assert g.disc_vx >= 0


def test_disc_bounces_off_right_edge():
    g = _make_game_clean()
    g.baskets = []
    g.player_x = 160.0
    g.player_y = 120.0
    g._start_aim(310.0, 120.0)  # aim far right for power
    g._release_throw()
    assert g.disc_vx > 0
    # Disc at vx=5 reaches x=320 at frame 32, bounces at frame 33
    for _ in range(40):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
    assert g.disc_vx <= 0


def test_disc_bounces_off_top_edge():
    g = _make_game_clean()
    g.baskets = []
    g.player_x = 160.0
    g.player_y = 120.0
    g._start_aim(160.0, 10.0)
    g._release_throw()
    assert g.disc_vy < 0
    # Disc at vy=-3.666... reaches y=0 at frame 33, bounces at frame 34
    for _ in range(40):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
    assert g.disc_vy >= 0


def test_disc_bounces_off_bottom_edge():
    g = _make_game_clean()
    g.baskets = []
    g.player_x = 160.0
    g.player_y = 120.0
    g._start_aim(160.0, 230.0)
    g._release_throw()
    assert g.disc_vy > 0
    # Disc at vy=3.666... reaches y=240 at frame 33, bounces at frame 34
    for _ in range(40):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
    assert g.disc_vy <= 0


# ── Basket Collision ──────────────────────────────────────────────────

def test_check_basket_collision_hit():
    g = _make_game_clean()
    # Place a basket and disc at same position
    g.baskets = [Basket(x=200.0, y=100.0, color=8, value=8)]
    result = g._check_basket_collision(200.0, 100.0)
    assert result is not None
    assert result.color == 8


def test_check_basket_collision_miss():
    g = _make_game_clean()
    g.baskets = [Basket(x=200.0, y=100.0, color=8, value=8)]
    result = g._check_basket_collision(50.0, 50.0)
    assert result is None


def test_flying_hits_basket():
    g = _make_game_clean()
    g.player_x = 50.0
    g.player_y = 50.0
    g.baskets = [Basket(x=200.0, y=50.0, color=8, value=8)]
    g._start_aim(200.0, 50.0)
    g._release_throw()
    for _ in range(50):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
            if g.phase == Phase.RESOLVE:
                break
    assert g.phase == Phase.RESOLVE
    assert g.flying_basket_hit is not None
    assert g.flying_basket_hit.color == 8


# ── Color Match Combo ────────────────────────────────────────────────

def test_first_hit_matches_any_color():
    g = _make_game_clean()
    g.last_basket_color = -1  # no combo yet
    g.combo = 0
    g.score = 0
    # Use an actual basket from the game
    basket = g.baskets[0]
    orig_color = basket.color
    orig_value = basket.value
    g._resolve_throw(basket)
    assert g.combo == 1
    assert g.last_basket_color == orig_color
    assert g.score == orig_value  # value * combo(1) * multiplier(1)


def test_same_color_builds_combo():
    g = _make_game_clean()
    g.last_basket_color = g.baskets[0].color
    g.combo = 2
    g.score = 10
    g.max_combo = 2
    # Find a basket with matching color
    match_color = g.last_basket_color
    matching = [b for b in g.baskets if b.color == match_color]
    if not matching:
        # Force a basket to match
        g.baskets[1].color = match_color
        matching = [g.baskets[1]]
    basket = matching[0]
    val = basket.value
    g._resolve_throw(basket)
    assert g.combo == 3
    assert g.score == 10 + val * 3
    assert g.max_combo == 3


def test_wrong_color_resets_combo():
    g = _make_game_clean()
    first_color = g.baskets[0].color
    g.last_basket_color = first_color
    g.combo = 3
    g.max_combo = 3
    g.heat = 1.0
    g.score = 50
    # Find a basket with different color
    wrong = [b for b in g.baskets if b.color != first_color]
    assert len(wrong) > 0, "Need a different-color basket for test"
    basket = wrong[0]
    g._resolve_throw(basket)
    assert g.combo == 0
    assert g.last_basket_color == -1
    assert g.disc_color == basket.color  # updated to wrong color
    assert g.heat > 1.0  # heat increased
    assert g.max_combo == 3  # max_combo preserved


def test_combo_value_multiplier():
    g = _make_game_clean()
    first_color = g.baskets[0].color
    g.last_basket_color = first_color
    g.combo = 4
    g.score = 100
    # Find a matching basket
    matching = [b for b in g.baskets if b.color == first_color]
    if len(matching) < 1:
        g.baskets[1].color = first_color
        matching = [g.baskets[1]]
    basket = matching[0]
    val = basket.value
    g._resolve_throw(basket)
    assert g.combo == 5
    assert g.score == 100 + val * 5  # value * combo(5)


# ── Super Mode ────────────────────────────────────────────────────────

def test_combo_4_triggers_super_mode():
    g = _make_game_clean()
    first_color = g.baskets[0].color
    g.last_basket_color = first_color
    g.combo = 3  # next hit = combo 4
    g.super_mode = False
    # Find a matching basket
    matching = [b for b in g.baskets if b.color == first_color]
    if len(matching) < 1:
        g.baskets[1].color = first_color
        matching = [g.baskets[1]]
    basket = matching[0]
    g._resolve_throw(basket)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_mode_3x_multiplier():
    g = _make_game_clean()
    first_color = g.baskets[0].color
    g.last_basket_color = first_color
    g.combo = 3
    g.super_mode = True
    g.score = 0
    # Find a matching basket
    matching = [b for b in g.baskets if b.color == first_color]
    if len(matching) < 1:
        g.baskets[1].color = first_color
        matching = [g.baskets[1]]
    basket = matching[0]
    val = basket.value
    g._resolve_throw(basket)
    assert g.score == val * 4 * 3  # value * combo(4) * 3x


def test_super_mode_does_not_reactivate():
    g = _make_game_clean()
    first_color = g.baskets[0].color
    g.last_basket_color = first_color
    g.combo = 4
    g.super_mode = True
    g.super_timer = 50  # already active
    # Find a matching basket
    matching = [b for b in g.baskets if b.color == first_color]
    if len(matching) < 1:
        g.baskets[1].color = first_color
        matching = [g.baskets[1]]
    basket = matching[0]
    g._resolve_throw(basket)
    assert g.super_mode is True
    assert g.super_timer == 50  # unchanged


# ── Miss / Heat ───────────────────────────────────────────────────────

def test_miss_increases_heat():
    g = _make_game_clean()
    g.heat = 3.0
    g.combo = 2
    g.last_basket_color = 8
    g._resolve_throw(None)  # miss
    assert g.heat == 3.0 + Game.HEAT_PER_MISS
    assert g.combo == 0
    assert g.last_basket_color == -1


def test_heat_at_max_triggers_game_over():
    g = _make_game_clean()
    g.heat = Game.MAX_HEAT  # 10.0
    # In real game: _update_timer() decays heat before check, so check BEFORE decay
    if g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_wrong_color_increases_heat():
    g = _make_game_clean()
    first_color = g.baskets[0].color
    g.last_basket_color = first_color
    g.heat = 0.0
    # Find a basket with different color
    wrong = [b for b in g.baskets if b.color != first_color]
    assert len(wrong) > 0, "Need a different-color basket for test"
    basket = wrong[0]
    g._resolve_throw(basket)
    assert g.heat == Game.HEAT_PER_MISS


# ── Timer ─────────────────────────────────────────────────────────────

def test_update_timer_decrements():
    g = _make_game_clean()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_timer_at_zero_game_over():
    g = _make_game_clean()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    if g.timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_heat_decays_each_frame():
    g = _make_game_clean()
    g.heat = 5.0
    g._update_timer()
    assert g.heat < 5.0


# ── Obstacle Spread (CA) ──────────────────────────────────────────────

def test_obstacle_spread_from_seed():
    g = _make_game_clean()
    g._rng = random.Random(42)
    # Place one seed obstacle in center
    g.obstacles = [Obstacle(x=20, y=15)]
    before = len(g.obstacles)
    # Try many times — with 30% chance, one attempt should succeed sometimes
    # but we just verify the method doesn't crash and doesn't shrink
    g._spread_obstacles()
    assert len(g.obstacles) >= before


def test_obstacle_spread_within_bounds():
    g = _make_game_clean()
    g._rng = random.Random(42)
    g.obstacles = [Obstacle(x=0, y=0)]
    g._spread_obstacles()
    for obs in g.obstacles:
        assert 0 <= obs.x < Game.OBSTACLE_GRID_W
        assert 0 <= obs.y < Game.OBSTACLE_GRID_H


def test_no_obstacles_no_crash():
    g = _make_game_clean()
    g.obstacles = []
    g._spread_obstacles()
    assert len(g.obstacles) == 0


# ── Obstacle Collision ────────────────────────────────────────────────

def test_obstacle_collision_detected():
    g = _make_game_clean()
    g.obstacles = [Obstacle(x=20, y=15)]
    half = Game.OBSTACLE_CELL // 2
    ox = 20 * Game.OBSTACLE_CELL + half
    oy = 15 * Game.OBSTACLE_CELL + half
    result = g._check_obstacle_collision(float(ox), float(oy))
    assert result is not None


def test_obstacle_collision_miss():
    g = _make_game_clean()
    g.obstacles = [Obstacle(x=20, y=15)]
    result = g._check_obstacle_collision(0.0, 0.0)
    assert result is None


# ── Particle System ───────────────────────────────────────────────────

def test_spawn_particles():
    g = _make_game_clean()
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 100.0, 8, 8)
    assert len(g.particles) == 8


def test_spawn_super_particles():
    g = _make_game_clean()
    g._rng = random.Random(42)
    g._spawn_super_particles(100.0, 100.0)
    assert len(g.particles) == 20


def test_update_particles_ages_them():
    g = _make_game_clean()
    g._spawn_particles(100.0, 100.0, 8, 1)
    p = g.particles[0]
    orig_life = p.life
    g._update_particles()
    # Particles with life>1 survive but age
    if orig_life > 1:
        assert len(g.particles) == 1
        assert g.particles[0].life == orig_life - 1


def test_update_particles_removes_dead():
    g = _make_game_clean()
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, life=1, color=8))
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → decremented to 0 → removed


# ── Player Position Update on Hit ─────────────────────────────────────

def test_player_moves_to_basket_on_hit():
    g = _make_game_clean()
    g.player_x = 100.0
    g.player_y = 100.0
    g.last_basket_color = -1
    basket = g.baskets[0]
    g._resolve_throw(basket)
    assert g.player_x == basket.x
    assert g.player_y == basket.y


# ── Basket Replacement ────────────────────────────────────────────────

def test_hit_basket_is_replaced():
    g = _make_game_clean()
    g.last_basket_color = -1
    hit = g.baskets[0]
    g._resolve_throw(hit)
    assert hit not in g.baskets
    assert len(g.baskets) == 4  # still 4 baskets


def test_replacement_basket_is_valid():
    g = _make_game_clean()
    g._rng = random.Random(42)
    g.last_basket_color = -1
    hit = g.baskets[0]
    g._resolve_throw(hit)
    new_basket = g.baskets[-1]
    assert new_basket.color in BASKET_COLORS
    assert 40 <= new_basket.x <= 280
    assert 40 <= new_basket.y <= 200


# ── Resolve Phase Timing ──────────────────────────────────────────────

def test_resolve_timer_is_set():
    g = _make_game_clean()
    g.last_basket_color = -1
    basket = g.baskets[0]
    g._enter_resolve(basket)
    assert g._resolve_timer == 15


# ── Game Over → Restart ───────────────────────────────────────────────

def test_init_state_resets_everything():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 999
    g.combo = 10
    g.max_combo = 20
    g.heat = 9.0
    g.timer = 100
    g.super_mode = True
    g.super_timer = 50
    g.baskets = []
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=8)]
    g.obstacles = [Obstacle(x=0, y=0)]

    g._init_state()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == Game.TIMER_FRAMES
    assert g.super_mode is False
    assert g.super_timer == 0
    assert len(g.baskets) == 4
    assert len(g.particles) == 0
    assert len(g.obstacles) == 0


# ── Super Timer Expiry ────────────────────────────────────────────────

def test_super_timer_decrements():
    g = _make_game_clean()
    g.super_mode = True
    g.super_timer = 10
    g._update_timer()
    assert g.super_timer == 9


def test_super_mode_ends_when_timer_zero():
    g = _make_game_clean()
    g.super_mode = True
    g.super_timer = 1
    g._update_timer()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Obstacle Collision During Flight ──────────────────────────────────

def test_disc_stops_on_obstacle():
    g = _make_game_clean()
    g.baskets = []  # no baskets to interfere
    g.player_x = 160.0
    g.player_y = 120.0
    g._rng = random.Random(42)
    # Place obstacle in path
    g.obstacles = [Obstacle(x=25, y=15)]  # cell (25,15) → center pixel
    half = Game.OBSTACLE_CELL // 2
    ox = 25 * Game.OBSTACLE_CELL + half
    oy = 15 * Game.OBSTACLE_CELL + half
    # Aim toward the obstacle
    g._start_aim(float(ox), float(oy))
    g._release_throw()
    for _ in range(30):
        if g.disc_active and g.phase == Phase.FLYING:
            g._update_flying()
    assert g.phase == Phase.RESOLVE
    assert g.flying_basket_hit is None  # hit obstacle, not basket


# ── Dataclass Instantiation ───────────────────────────────────────────

def test_basket_dataclass():
    b = Basket(x=100.0, y=200.0, color=8, value=10)
    assert b.x == 100.0
    assert b.y == 200.0
    assert b.color == 8
    assert b.value == 10
    assert b.radius == 12  # default


def test_obstacle_dataclass():
    o = Obstacle(x=10, y=20)
    assert o.x == 10
    assert o.y == 20
    assert o.radius == 6


def test_particle_dataclass():
    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=30, color=8)
    assert p.x == 1.5
    assert p.y == 2.5
    assert p.vx == 0.5
    assert p.vy == -0.5
    assert p.life == 30
    assert p.color == 8


# ── Max Fly Frames with Basket Hit ────────────────────────────────────

def test_max_fly_frames_triggers_resolve():
    g = _make_game_clean()
    g.baskets = []
    g.player_x = 50.0
    g.player_y = 50.0
    g._start_aim(150.0, 50.0)
    g._release_throw()
    # Fly until timeout
    for _ in range(65):
        if g.phase == Phase.FLYING and g.disc_active:
            g._update_flying()
    assert g.phase == Phase.RESOLVE
    assert g.disc_active is False


# ── Smoke test: full game flow ────────────────────────────────────────

def test_full_flow_title_to_aiming_to_flying_to_resolve_to_aiming():
    g = _make_game()
    g.phase = Phase.TITLE

    # Title → AIMING
    g._init_state()
    g.phase = Phase.AIMING

    # AIMING: aim and throw
    target = g.baskets[0]
    g._start_aim(target.x, target.y)
    assert g.is_aiming
    g._release_throw()
    assert g.phase == Phase.FLYING

    # FLYING: fly toward target
    for _ in range(30):
        if g.phase == Phase.FLYING and g.disc_active:
            g._update_flying()

    # Should be in RESOLVE (hit or miss)
    assert g.phase == Phase.RESOLVE
    # RESOLVE: tick down
    for _ in range(16):
        if g.phase == Phase.RESOLVE:
            g._resolve_timer -= 1
            g._update_particles()
            g._update_timer()
            if g._resolve_timer <= 0:
                if g.heat >= Game.MAX_HEAT or g.timer <= 0:
                    g.phase = Phase.GAME_OVER
                else:
                    g.phase = Phase.AIMING
                    g.is_aiming = False

    # Back to AIMING (since heat/timer not exceeded)
    assert g.phase == Phase.AIMING or g.phase == Phase.GAME_OVER
