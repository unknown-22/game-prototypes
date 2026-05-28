"""Tests for ECHO SLIDE game logic."""

from __future__ import annotations

import random
import sys

sys.path.insert(0, "prototypes/077_echo_slide")
import main  # noqa: E402


def _make_game(seed: int = 42) -> main.Game:
    g = main.Game.__new__(main.Game)
    g._init_state()
    g.phase = main.Phase.AIMING
    g.rng = random.Random(seed)
    return g


# ---- Ring Detection ----
def test_score_ring_center():
    g = _make_game()
    assert g._score_ring(5) == main.SCORE_CENTER
    assert g._score_ring(g._ring_center_r()) == main.SCORE_CENTER


def test_score_ring_mid():
    g = _make_game()
    assert g._score_ring(20) == main.SCORE_MID


def test_score_ring_outer():
    g = _make_game()
    assert g._score_ring(40) == main.SCORE_OUTER


def test_score_ring_miss():
    g = _make_game()
    assert g._score_ring(60) == 0


def test_ring_name():
    g = _make_game()
    assert g._ring_name(5) == "BULLSEYE"
    assert g._ring_name(20) == "MIDDLE"
    assert g._ring_name(40) == "OUTER"
    assert g._ring_name(60) == "MISS"


def test_ring_shrink_per_round():
    g = _make_game()
    g.round = 1
    r1 = g._ring_outer_r()
    g.round = 3
    r3 = g._ring_outer_r()
    assert r3 < r1
    assert r3 >= 10


def test_dist_to_target():
    g = _make_game()
    assert g._dist_to_target(main.TARGET_CX, main.TARGET_CY) == 0.0
    assert g._dist_to_target(main.TARGET_CX + 3, main.TARGET_CY + 4) == 5.0


# ---- COMBO System ----
def test_combo_same_color_builds():
    g = _make_game()
    g.ghost_color = main.COLORS[0]
    g.ghost_landing_dist = 30.0
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.combo = 0
    g._handle_landing()
    assert g.combo == 1

    g.ghost_color = main.COLORS[0]
    g.ghost_landing_dist = 20.0
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.phase = main.Phase.AIMING
    g._handle_landing()
    assert g.combo == 2


def test_combo_resets_on_different_color():
    g = _make_game()
    g.ghost_color = main.COLORS[0]
    g.ghost_landing_dist = 30.0
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.combo = 2
    g._handle_landing()
    assert g.combo == 3

    g.ghost_color = main.COLORS[0]
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[1])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.phase = main.Phase.AIMING
    g._handle_landing()
    assert g.combo == 1


def test_combo_resets_on_miss():
    g = _make_game()
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.combo = 5
    g._handle_miss()
    assert g.combo == 0


def test_max_combo_tracks_high():
    g = _make_game()
    g.ghost_color = main.COLORS[0]
    g.ghost_landing_dist = 30.0
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.combo = 0
    g._handle_landing()
    assert g.max_combo == 1
    g.phase = main.Phase.AIMING
    g._handle_landing()
    assert g.max_combo == 2


def test_combo_starts_at_1_on_first_hit():
    g = _make_game()
    g.ghost_color = -1
    g.ghost_landing_dist = -1.0
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g._handle_landing()
    assert g.combo == 1


# ---- Scoring ----
def test_compute_score_basic():
    g = _make_game()
    assert g._compute_score(100, 1, echo=False, trail=False, super_slide=False) == 100
    assert g._compute_score(100, 3, echo=False, trail=False, super_slide=False) == 300


def test_compute_score_echo():
    g = _make_game()
    gained = g._compute_score(100, 1, echo=True, trail=False, super_slide=False)
    assert gained == int(100 * main.ECHO_BONUS_MULT)


def test_compute_score_trail():
    g = _make_game()
    gained = g._compute_score(100, 1, echo=False, trail=True, super_slide=False)
    assert gained == int(100 * main.TRAIL_BONUS_MULT)


def test_compute_score_super_slide():
    g = _make_game()
    gained = g._compute_score(100, 1, echo=False, trail=False, super_slide=True)
    assert gained == 200


def test_compute_score_all_bonuses():
    g = _make_game()
    gained = g._compute_score(100, 3, echo=True, trail=True, super_slide=True)
    expected = int(100 * 3 * main.ECHO_BONUS_MULT * main.TRAIL_BONUS_MULT) * main.SUPER_SLIDE_MULT
    assert gained == expected


# ---- ECHO Bonus ----
def test_echo_bonus_closer_to_center():
    g = _make_game()
    g.ghost_landing_dist = 40.0
    g.ghost_path = [(100.0, 100.0), (160.0, 200.0)]
    g.puck_path = [(100.0, 100.0), (160.0, 180.0)]
    echo, trail = g._check_echo_bonus(30.0)
    assert echo is True


def test_echo_bonus_not_closer():
    g = _make_game()
    g.ghost_landing_dist = 20.0
    g.ghost_path = [(100.0, 100.0)]
    g.puck_path = [(100.0, 100.0)]
    echo, trail = g._check_echo_bonus(40.0)
    assert echo is False


def test_trail_bonus_overlap():
    g = _make_game()
    g.ghost_landing_dist = 40.0
    g.ghost_path = [(100.0, 100.0), (150.0, 150.0)]
    g.puck_path = [(102.0, 102.0), (150.0, 150.0)]
    echo, trail = g._check_echo_bonus(25.0)
    assert trail is True


def test_trail_bonus_no_overlap():
    g = _make_game()
    g.ghost_landing_dist = 40.0
    g.ghost_path = [(100.0, 100.0)]
    g.puck_path = [(200.0, 200.0)]
    echo, trail = g._check_echo_bonus(25.0)
    assert trail is False


def test_no_echo_on_first_throw():
    g = _make_game()
    g.ghost_landing_dist = -1.0
    g.ghost_path = []
    g.puck_path = [(100.0, 100.0)]
    echo, trail = g._check_echo_bonus(25.0)
    assert echo is False
    assert trail is False


# ---- SUPER SLIDE ----
def test_super_slide_activates_at_combo_3():
    g = _make_game()
    g.ghost_color = main.COLORS[0]
    g.ghost_landing_dist = 30.0
    g.combo = 2
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g._handle_landing()
    assert g.combo == 3
    assert g.super_slide is True
    assert g.super_slide_frames == 60


def test_super_slide_not_active_at_combo_2():
    g = _make_game()
    g.ghost_color = main.COLORS[0]
    g.ghost_landing_dist = 30.0
    g.combo = 1
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g._handle_landing()
    assert g.combo == 2
    assert g.super_slide is False


# ---- Round System ----
def test_round_threshold():
    g = _make_game()
    assert g.threshold == 500


def test_next_puck_advances_round():
    g = _make_game()
    g.score = 600
    g.threshold = 500
    g.pucks_remaining = 1
    g.round = 1
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g._next_puck()
    assert g.round == 2
    assert g.pucks_remaining == main.PUCKS_PER_ROUND
    assert g.threshold == 1000
    assert g.phase == main.Phase.AIMING


def test_next_puck_game_over():
    g = _make_game()
    g.score = 200
    g.threshold = 500
    g.pucks_remaining = 1
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g._next_puck()
    assert g.phase == main.Phase.GAME_OVER


def test_next_puck_continues():
    g = _make_game()
    g.pucks_remaining = 5
    g.combo = 2
    g.round = 1
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g._next_puck()
    assert g.pucks_remaining == 4
    assert g.phase == main.Phase.AIMING
    assert g.puck is None
    assert g.puck_path == []


# ---- Miss Handling ----
def test_handle_miss_resets_combo():
    g = _make_game()
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(100.0, 100.0)]
    g.combo = 4
    g.super_slide = True
    g._handle_miss()
    assert g.combo == 0
    assert g.super_slide is False
    assert g.phase == main.Phase.SCORING


def test_handle_miss_saves_ghost():
    g = _make_game()
    g.puck = main.Puck(x=main.TARGET_CX, y=main.TARGET_CY, color=main.COLORS[0])
    g.puck_path = [(100.0, 100.0), (160.0, 200.0)]
    g._handle_miss()
    assert g.ghost_path == g.puck_path
    assert g.ghost_color == main.COLORS[0]


# ---- Puck Physics ----
def test_puck_friction():
    g = _make_game()
    g.phase = main.Phase.SLIDING
    g.puck = main.Puck(x=100.0, y=100.0, vx=5.0, vy=3.0, color=main.COLORS[0])
    g._update_puck()
    assert g.puck.vx < 5.0
    assert g.puck.vy < 3.0
    assert g.puck.vx > 0
    assert g.puck.vy > 0


def test_puck_stops_at_threshold():
    g = _make_game()
    g.phase = main.Phase.SLIDING
    g.puck = main.Puck(
        x=main.TARGET_CX,
        y=main.TARGET_CY,
        vx=0.1,
        vy=0.1,
        color=main.COLORS[0],
    )
    g._update_puck()
    assert not g.puck.active
    assert g.puck.landed


# ---- Landing Scoring ----
def test_handle_landing_center_scores():
    g = _make_game()
    g.ghost_landing_dist = -1.0
    g.puck = main.Puck(
        x=float(main.TARGET_CX),
        y=float(main.TARGET_CY),
        color=main.COLORS[0],
    )
    g.puck_path = [(float(main.TARGET_CX), float(main.TARGET_CY))]
    g.score = 0
    g._handle_landing()
    assert g.score == main.SCORE_CENTER
    assert g.combo == 1


def test_handle_landing_outside_ring_is_miss():
    g = _make_game()
    g.ghost_landing_dist = -1.0
    g.puck = main.Puck(x=0.0, y=0.0, color=main.COLORS[0])
    g.puck_path = [(0.0, 0.0)]
    g.score = 100
    g.combo = 3
    g._handle_landing()
    assert g.combo == 0
    assert g.score == 100


# ---- Initialization ----
def test_init_state():
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.round == 1
    assert g.pucks_remaining == main.PUCKS_PER_ROUND
    assert g.threshold == 500
    assert g.puck is None
    assert g.ghost_landing_dist == -1.0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.super_slide is False


def test_reset():
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.round = 4
    g.puck = main.Puck(x=100.0, y=100.0, color=main.COLORS[0])
    g.ghost_landing_dist = 30.0
    g.super_slide = True
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.round == 1
    assert g.puck is None
    assert g.ghost_landing_dist == -1.0
    assert g.super_slide is False
    assert g.phase == main.Phase.AIMING


# ---- Pick Color ----
def test_pick_color_returns_valid():
    g = _make_game()
    for _ in range(20):
        c = g._pick_color()
        assert c in main.COLORS


# ---- Launch Puck ----
def test_launch_puck_creates_puck():
    g = _make_game()
    g.current_color = main.COLORS[0]
    g.aim_origin = (160, 50)
    g.aim_end = (160, 100)
    g.aiming = True
    g.phase = main.Phase.AIMING
    g._launch_puck()
    assert g.phase == main.Phase.SLIDING
    assert g.puck is not None
    assert g.puck.color == main.COLORS[0]
    assert g.puck.vy > 0
    assert not g.aiming


def test_launch_puck_too_small_drag_cancels():
    g = _make_game()
    g.current_color = main.COLORS[0]
    g.aim_origin = (160, 50)
    g.aim_end = (160, 50)
    g.aiming = True
    g.phase = main.Phase.AIMING
    g._launch_puck()
    assert not g.aiming
    assert g.phase == main.Phase.AIMING
    assert g.puck is None


def test_launch_puck_horizontal():
    g = _make_game()
    g.current_color = main.COLORS[0]
    g.aim_origin = (160, 50)
    g.aim_end = (260, 50)
    g.aiming = True
    g.phase = main.Phase.AIMING
    g._launch_puck()
    assert g.puck is not None
    assert g.puck.vx > 0
    assert abs(g.puck.vy) < 0.01


# ---- Floating Text / Particles ----
def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_update_floating_texts():
    g = _make_game()
    g._spawn_floating_text(100, 100, "A", 7)
    g.floating_texts[0].life = 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_particles():
    g = _make_game()
    g.particles.append(main.Particle(100, 100, 1, 0, 7, 1))
    g._update_particles()
    assert len(g.particles) == 0


# ---- Edge Cases ----
def test_miss_on_out_of_bounds():
    g = _make_game()
    g.phase = main.Phase.SLIDING
    g.puck = main.Puck(x=-10.0, y=100.0, vx=-1.0, vy=0.0, color=main.COLORS[0])
    g.puck_path = [(100.0, 100.0)]
    g.combo = 3
    g._update_puck()
    assert not g.puck.active
    assert g.combo == 0
    assert g.phase == main.Phase.SCORING
