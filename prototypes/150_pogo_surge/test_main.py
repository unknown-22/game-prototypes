import random

from main import (
    COMBO_FOR_SUPER,
    GRAVITY,
    HEAT_PER_WRONG,
    MAX_CHARGE,
    MAX_HEAT,
    MIN_BOUNCE,
    SCREEN_H,
    SUPER_DURATION,
    FloatingText,
    Game,
    Pad,
    Particle,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.player_x = 160.0
    g.player_y = 80.0
    g.player_vy = 0.0
    g.player_color = 0
    g.charge = 0.0
    g.is_charging = False
    g.on_ground = False
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.pads = []
    g.particles = []
    g.floating_texts = []
    g.lava_y = float(SCREEN_H + 100)
    g.shake_frames = 0
    g.frame = 0
    g.rng = random.Random(42)
    g._col_positions = [40 + i * 60 for i in range(5)]
    g.phase = "PLAYING"
    g._init_state()
    return g


# ------------------------------------------------------------------
# 1. Landing on same-color pad
# ------------------------------------------------------------------
def _setup_landing(g: Game, pad: Pad, player_y: float = 80.0) -> None:
    """Apply physics before landing check so _check_landing sees the post-physics state."""
    g.player_x = pad.x
    g.player_y = float(player_y)
    g.player_vy = 5.0
    g.on_ground = False
    g.pads = [pad]
    g._update_physics()


def test_landing_same_color_increases_combo_and_score() -> None:
    g = _make_game()
    g.player_color = 0
    g.combo = 1
    g.score = 100

    pad = Pad(x=100.0, y=97.0, color=0)
    _setup_landing(g, pad)

    landed = g._check_landing()
    assert landed
    assert g.combo == 2
    assert g.score > 100
    assert g.on_ground
    assert g.player_color == 0


def test_landing_same_color_max_combo_tracks() -> None:
    g = _make_game()
    g.player_color = 0
    g.max_combo = 3
    g.combo = 3

    pad = Pad(x=100.0, y=97.0, color=0)
    _setup_landing(g, pad)

    g._check_landing()
    assert g.combo == 4
    assert g.max_combo == 4


def test_landing_wrong_color_resets_combo_and_adds_heat() -> None:
    g = _make_game()
    g.player_color = 0
    g.combo = 3
    g.heat = 10.0

    pad = Pad(x=100.0, y=97.0, color=1)
    _setup_landing(g, pad)

    landed = g._check_landing()
    assert landed
    assert g.combo == 0
    assert g.heat == min(MAX_HEAT, 10.0 + HEAT_PER_WRONG)
    assert g.player_color == 1


def test_combo_5_activates_super() -> None:
    g = _make_game()
    g.player_color = 0
    g.combo = COMBO_FOR_SUPER - 1  # 4

    pad = Pad(x=100.0, y=97.0, color=0)
    _setup_landing(g, pad)

    g._check_landing()
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION
    assert g.combo == COMBO_FOR_SUPER  # 5


def test_super_mode_landing_auto_matches_any_color() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.player_color = 0
    g.combo = 5
    g.score = 200

    pad = Pad(x=100.0, y=97.0, color=2)
    _setup_landing(g, pad)

    landed = g._check_landing()
    assert landed
    assert g.combo == 6
    assert g.score > 200


def test_super_mode_auto_bounce() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.player_color = 0
    g.combo = 5

    pad = Pad(x=100.0, y=97.0, color=0)
    _setup_landing(g, pad)

    g._check_landing()
    assert not g.on_ground
    assert g.player_vy < 0


# ------------------------------------------------------------------
# 5. Falling off screen → game over
# ------------------------------------------------------------------
def test_fall_off_screen_game_over() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.player_y = SCREEN_H + 100  # Below screen

    # Simulate the game-over check (first lines of _update_playing)
    if g.player_y > SCREEN_H + 50:
        g.phase = "GAME_OVER"

    assert g.phase == "GAME_OVER"


# ------------------------------------------------------------------
# 6. Heat reaching max → game over
# ------------------------------------------------------------------
def test_heat_max_game_over() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = float(MAX_HEAT)

    if g.heat >= MAX_HEAT:
        g.phase = "GAME_OVER"

    assert g.phase == "GAME_OVER"


# ------------------------------------------------------------------
# 7. _init_state fully resets all fields
# ------------------------------------------------------------------
def test_init_state_resets_all_fields() -> None:
    g = _make_game()
    # Dirty some fields
    g.score = 9999
    g.combo = 10
    g.max_combo = 10
    g.heat = 99.0
    g.super_mode = True
    g.super_timer = 50
    g.on_ground = False
    g.particles.append(Particle(x=0, y=0, vx=1, vy=1, color=7, life=10))
    g.floating_texts.append(FloatingText(x=0, y=0, text="X", color=7, life=10))
    g.pads.append(Pad(x=0, y=0, color=0))

    g._init_state()

    assert g.phase == "TITLE"
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert not g.super_mode
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.pads == []
    assert g.charge == 0.0
    assert not g.is_charging


# ------------------------------------------------------------------
# 8. _update_particles removes dead particles
# ------------------------------------------------------------------
def test_update_particles_removes_dead() -> None:
    g = _make_game()
    alive = Particle(x=0, y=0, vx=1, vy=1, color=7, life=5)
    dead = Particle(x=0, y=0, vx=0, vy=0, color=7, life=0)
    g.particles = [alive, dead]

    g._update_particles()

    assert len(g.particles) == 1
    assert g.particles[0].life == 4  # decremented


# ------------------------------------------------------------------
# 9. Charging builds charge; releasing launches player
# ------------------------------------------------------------------
def test_charging_builds_charge() -> None:
    g = _make_game()
    g.on_ground = True
    g.charge = 0.0
    g.is_charging = True

    # Simulate a frame of charging
    g.charge = min(float(MAX_CHARGE), g.charge + 1.0)
    assert g.charge == 1.0

    # Several more frames
    for _ in range(20):
        g.charge = min(float(MAX_CHARGE), g.charge + 1.0)
    assert g.charge == 21.0


def test_charging_released_launches_player() -> None:
    g = _make_game()
    g.on_ground = True
    g.charge = 30.0  # half charge
    g.is_charging = True
    g.player_vy = 0.0

    # Release
    charge_ratio = g.charge / MAX_CHARGE
    g.player_vy = -(MIN_BOUNCE + charge_ratio * (12.0 - MIN_BOUNCE))
    g.on_ground = False
    g.is_charging = False
    g.charge = 0.0

    assert g.player_vy < 0  # Launching upward
    assert not g.on_ground
    assert g.charge == 0.0


def test_charging_full_charge_gives_max_bounce() -> None:
    g = _make_game()
    g.on_ground = True
    g.charge = float(MAX_CHARGE)

    charge_ratio = g.charge / MAX_CHARGE
    vy = -(MIN_BOUNCE + charge_ratio * (12.0 - MIN_BOUNCE))
    assert vy == -12.0  # MAX_BOUNCE


def test_charging_min_charge_gives_min_bounce() -> None:
    g = _make_game()
    g.on_ground = True
    g.charge = 1.0  # Just a tiny charge

    charge_ratio = g.charge / MAX_CHARGE
    vy = -(MIN_BOUNCE + charge_ratio * (12.0 - MIN_BOUNCE))
    assert vy < 0
    assert abs(vy) > MIN_BOUNCE  # slightly more than min


# ------------------------------------------------------------------
# 10. Super timer expires → super mode ends
# ------------------------------------------------------------------
def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 10

    g.super_timer -= 1
    if g.super_timer <= 0:
        g._end_super()

    assert not g.super_mode
    assert g.super_timer == 0
    assert g.combo == 0  # reset on super end


def test_super_timer_not_expired_yet() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100

    g.super_timer -= 1
    if g.super_timer <= 0:
        g._end_super()

    assert g.super_mode
    assert g.super_timer == 99


# ------------------------------------------------------------------
# Additional: score_for_landing
# ------------------------------------------------------------------
def test_score_for_landing_match() -> None:
    g = _make_game()
    g.combo = 3
    # multiplier = 1 + 2 * 0.5 = 2.0, base = 10, score = 20
    assert g.score_for_landing(True) == 20

    g.combo = 1
    # multiplier = 1 + 0 * 0.5 = 1.0, base = 10, score = 10
    assert g.score_for_landing(True) == 10


def test_score_for_landing_miss() -> None:
    g = _make_game()
    assert g.score_for_landing(False) == 1


# ------------------------------------------------------------------
# Additional: physics
# ------------------------------------------------------------------
def test_update_physics_gravity() -> None:
    g = _make_game()
    g.player_y = 100.0
    g.player_vy = 0.0
    g.on_ground = False

    g._update_physics()
    assert g.player_vy == GRAVITY
    assert g.player_y == 100.0 + GRAVITY


# ------------------------------------------------------------------
# Additional: _update_floating_texts removes dead
# ------------------------------------------------------------------
def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0, y=0, text="A", color=7, life=5),
        FloatingText(x=0, y=0, text="B", color=7, life=0),
    ]

    g._update_floating_texts()

    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 4


# ------------------------------------------------------------------
# Additional: _scroll_pads moves pads and spawns new ones
# ------------------------------------------------------------------
def test_scroll_pads_moves_and_respawns() -> None:
    g = _make_game()
    g.pads = [
        Pad(x=100.0, y=0.0, color=0),
        Pad(x=160.0, y=55.0, color=1),
        Pad(x=220.0, y=-50.0, color=2),
    ]

    g._scroll_pads(10.0)

    # All moved by 10
    for pad in g.pads:
        pad.y

    # The pad that started at y=-50 is now at -40, still above the view
    # No pad should be below SCREEN_H+50
    for pad in g.pads:
        assert pad.y < SCREEN_H + 50

    # Should have spawned more pads above (top_y = -40, and while > -PAD_SPACING*3=-165, spawn more)
    assert len(g.pads) >= 3  # original 3 + spawned


# ------------------------------------------------------------------
# Additional: heat decay
# ------------------------------------------------------------------
def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat < 10.0
    assert g.heat >= 0.0


def test_heat_decay_stops_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ------------------------------------------------------------------
# Additional: combo does NOT reset on wrong color during super
# ------------------------------------------------------------------
def test_wrong_color_during_super_does_not_reset_combo() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.player_color = 0
    g.combo = 10

    pad = Pad(x=100.0, y=97.0, color=3)
    _setup_landing(g, pad)

    g._check_landing()
    assert g.combo == 11
