"""test_imports.py — Headless logic tests for HURDLE CHAIN (255_hurdle_chain)."""
from __future__ import annotations

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    Game,
    Phase,
    Hurdle,
    Particle,
    FloatingText,
    SCREEN_W,
    GROUND_Y,
    HURDLE_WIDTH,
    HURDLE_Y,
    COLOR_VALS,
    COLOR_NAMES,
    COLOR_CYCLE_FRAMES,
    COMBO_THRESHOLD,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_CRASH,
    SCROLL_START,
    SCROLL_END,
    JUMP_VY,
    SUPER_DURATION,
    STUN_MISMATCH,
    STUN_CRASH,
    TIMER_MAX,
)

PLAYER_X = SCREEN_W // 4  # 80


def _make_game(seed: int = 42) -> Game:
    """Factory: create headless Game instance with seeded RNG."""
    g = Game(headless=True)
    g.rng = random.Random(seed)
    g._reset()
    g.phase = Phase.PLAYING
    return g


def _place_hurdle_at_player(g: Game, color: int | None = None) -> Hurdle:
    """Place a hurdle with its center aligned to player_x."""
    if color is None:
        color = g._player_color()
    # Center = h.x + HURDLE_WIDTH/2 should equal PLAYER_X
    hx = float(PLAYER_X - HURDLE_WIDTH // 2)
    h = Hurdle(x=hx, y=float(HURDLE_Y), color=color)
    g.hurdles = [h]
    return h


# ── Data structures ──


def test_hurdle_dataclass() -> None:
    h = Hurdle(x=100.0, y=HURDLE_Y, color=COLOR_VALS[0])
    assert h.x == 100.0
    assert h.y == HURDLE_Y
    assert h.color == 8  # RED
    assert h.cleared is False
    assert h.scored is False


def test_particle_dataclass() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, color=11, life=20)
    assert p.x == 50.0
    assert p.life == 20


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=80.0, text="+10", color=11, life=30)
    assert ft.text == "+10"
    assert ft.color == 11
    assert ft.life == 30


# ── Constants ──


def test_color_constants() -> None:
    assert len(COLOR_VALS) == 4
    assert COLOR_VALS == (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
    assert len(COLOR_NAMES) == 4
    assert COLOR_NAMES == ("RED", "LIME", "DARK_BLUE", "YELLOW")


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Initialization ──


def test_reset_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.player_y == float(GROUND_Y)
    assert g.player_vy == 0.0
    assert g.player_color_idx == 0
    assert g.player_on_ground is True
    assert g.player_stun == 0
    assert len(g.hurdles) == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.heat == 0.0
    assert g.timer_frames == TIMER_MAX
    assert g.scroll_speed == SCROLL_START
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.ghost_trail) == 0


def test_player_color() -> None:
    g = _make_game()
    assert g._player_color() == 8  # RED at idx 0
    assert g._player_color_name() == "RED"


def test_color_cycle() -> None:
    g = _make_game()
    assert g.player_color_idx == 0
    for _ in range(COLOR_CYCLE_FRAMES):
        g._update_color_cycle()
    assert g.player_color_idx == 1  # LIME
    assert g._player_color() == 11


# ── Jump and physics ──


def test_jump() -> None:
    g = _make_game()
    assert g.player_on_ground is True
    g._jump()
    assert g.player_on_ground is False
    assert g.player_vy == JUMP_VY


def test_jump_blocked_when_airborne() -> None:
    g = _make_game()
    g._jump()
    vy_after_jump = g.player_vy
    g._jump()  # double jump should be ignored
    assert g.player_vy == vy_after_jump


def test_jump_blocked_when_stunned() -> None:
    g = _make_game()
    g.player_stun = 5
    g._jump()
    assert g.player_on_ground is True  # didn't jump


def test_gravity_and_landing() -> None:
    g = _make_game()
    g._jump()
    # Need ~31 frames to complete the jump arc (apex + landing)
    # vy=-7.0, gravity=0.45: apex at 15-16f, land at ~31f
    for _ in range(35):
        g._update_player()
    assert g.player_y == float(GROUND_Y)
    assert g.player_vy == 0.0
    assert g.player_on_ground is True


def test_stun_decrements() -> None:
    g = _make_game()
    g.player_stun = STUN_CRASH
    g._update_player()
    assert g.player_stun == STUN_CRASH - 1


# ── Hurdle spawning ──


def test_spawn_hurdle() -> None:
    g = _make_game()
    assert len(g.hurdles) == 0
    g._spawn_hurdle()
    assert len(g.hurdles) == 1
    h = g.hurdles[0]
    assert h.x >= SCREEN_W + 80
    assert h.color in COLOR_VALS
    assert h.cleared is False
    assert h.scored is False


def test_spawn_hurdle_gap() -> None:
    g = _make_game()
    g._spawn_hurdle()
    h1_x = g.hurdles[0].x
    g._spawn_hurdle()
    h2_x = g.hurdles[1].x
    gap = h2_x - h1_x
    assert 80 <= gap <= 140


def test_update_hurdles_move_left() -> None:
    g = _make_game()
    g._spawn_hurdle()
    orig_x = g.hurdles[0].x
    g._update_hurdles()
    assert g.hurdles[0].x == orig_x - g.scroll_speed


def test_update_hurdles_remove_offscreen() -> None:
    g = _make_game()
    g._spawn_hurdle()
    g.hurdles[0].x = -100  # far left
    g._update_hurdles()
    assert len(g.hurdles) == 0


# ── Hurdle clearing (scoring) ──


def test_hurdle_clear_match() -> None:
    g = _make_game()
    _place_hurdle_at_player(g)
    g.player_y = HURDLE_Y - 5  # airborne above hurdle
    g.player_on_ground = False
    g._check_hurdle_clear()
    h = g.hurdles[0]
    assert h.scored is True
    assert h.cleared is True
    assert g.combo == 1
    assert g.heat == 0.0


def test_hurdle_clear_mismatch() -> None:
    g = _make_game()
    mismatch_color = COLOR_VALS[(g.player_color_idx + 1) % 4]
    _place_hurdle_at_player(g, mismatch_color)
    g.player_y = HURDLE_Y - 5
    g.player_on_ground = False
    g._check_hurdle_clear()
    h = g.hurdles[0]
    assert h.scored is True
    assert h.cleared is False
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g.player_stun == STUN_MISMATCH


def test_hurdle_crash() -> None:
    g = _make_game()
    _place_hurdle_at_player(g)
    g.player_y = GROUND_Y  # on ground, not jumping
    g.player_on_ground = True
    g._check_hurdle_clear()
    assert g.heat == HEAT_CRASH
    assert g.player_stun == STUN_CRASH
    assert g.combo == 0


def test_hurdle_clear_combo_chain() -> None:
    g = _make_game()
    for i in range(3):
        _place_hurdle_at_player(g)
        g.player_y = HURDLE_Y - 5
        g.player_on_ground = False
        g._check_hurdle_clear()
    assert g.combo == 3


def test_hurdle_clear_score_calculation() -> None:
    g = _make_game()
    for i in range(2):
        _place_hurdle_at_player(g)
        g.player_y = HURDLE_Y - 5
        g.player_on_ground = False
        g._check_hurdle_clear()
    # Score: combo 1 = 10*1 = 10, combo 2 = 10*2 = 20, total = 30
    assert g.combo == 2
    assert g.score == 30


# ── SUPER activation ──


def test_super_activation() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1  # 3
    _place_hurdle_at_player(g)
    g.player_y = HURDLE_Y - 5
    g.player_on_ground = False
    g._check_hurdle_clear()
    assert g.combo == COMBO_THRESHOLD  # 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_any_color_match() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    any_color = COLOR_VALS[(g.player_color_idx + 2) % 4]
    _place_hurdle_at_player(g, any_color)
    g.player_y = HURDLE_Y - 5
    g.player_on_ground = False
    g._check_hurdle_clear()
    assert g.hurdles[0].cleared is True
    assert g.combo == 1


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.combo = 1
    _place_hurdle_at_player(g)
    g.player_y = HURDLE_Y - 5
    g.player_on_ground = False
    score_before = g.score
    g._check_hurdle_clear()
    # combo goes to 2, score = 10 * 2 * 3 (super multiplier) = 60
    assert g.combo == 2
    assert g.score - score_before == 60


def test_super_timer_decrement() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g._update_super()
    assert g.super_timer == SUPER_DURATION - 1


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Heat system ──


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - 0.02


def test_heat_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX  # exactly 100
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_does_not_decay_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_frozen_in_super() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0  # unchanged


# ── Timer ──


def test_timer_decrements() -> None:
    g = _make_game()
    g._update_timer()
    assert g.timer_frames == TIMER_MAX - 1


def test_timer_game_over() -> None:
    g = _make_game()
    g.timer_frames = 1
    g._update_timer()
    assert g.timer_frames == 0
    assert g.phase == Phase.GAME_OVER


# ── Scroll speed ──


def test_scroll_speed_start() -> None:
    g = _make_game()
    assert g.scroll_speed == SCROLL_START


def test_scroll_speed_increases() -> None:
    g = _make_game()
    g.play_time = TIMER_MAX // 2
    g._update_scroll_speed()
    mid = SCROLL_START + (SCROLL_END - SCROLL_START) * 0.5
    assert abs(g.scroll_speed - mid) < 0.01


def test_scroll_speed_at_end() -> None:
    g = _make_game()
    g.play_time = TIMER_MAX
    g._update_scroll_speed()
    assert abs(g.scroll_speed - SCROLL_END) < 0.01


# ── Max combo tracking ──


def test_max_combo_tracks_peak() -> None:
    g = _make_game()
    for i in range(5):
        _place_hurdle_at_player(g)
        g.player_y = HURDLE_Y - 5
        g.player_on_ground = False
        g._check_hurdle_clear()
    assert g.combo == 5
    assert g.max_combo == 5


def test_max_combo_persists_after_reset() -> None:
    g = _make_game()
    for i in range(3):
        _place_hurdle_at_player(g)
        g.player_y = HURDLE_Y - 5
        g.player_on_ground = False
        g._check_hurdle_clear()
    assert g.max_combo == 3
    # Mismatch resets combo
    mismatch_color = COLOR_VALS[(g.player_color_idx + 1) % 4]
    _place_hurdle_at_player(g, mismatch_color)
    g._check_hurdle_clear()
    assert g.combo == 0
    assert g.max_combo == 3  # max persists


# ── Best score ──


def test_best_score_updated_on_game_over() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 0
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


# ── Ghost trail ──


def test_record_ghost() -> None:
    g = _make_game()
    assert len(g.ghost_trail) == 0
    g.play_time = 4
    g._record_ghost()
    assert len(g.ghost_trail) == 0  # frame 4, not recorded
    g.play_time = 5
    g._record_ghost()
    assert len(g.ghost_trail) == 1  # frame 5, recorded
    px, py = g.ghost_trail[0]
    assert px == float(SCREEN_W // 4)


# ── Particles ──


def test_spawn_particles() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 150, 5, 8)  # RED
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8
        assert p.life >= 15


def test_spawn_particles_rainbow() -> None:
    g = _make_game()
    g._spawn_particles(100, 150, 10, -1)  # -1 = rainbow
    assert len(g.particles) == 10
    colors = {p.color for p in g.particles}
    assert colors.issubset(set(COLOR_VALS))


def test_update_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 150, 3, 8)
    for _ in range(3):
        g._update_particles()
    for p in g.particles:
        assert p.life >= 13  # started at 15-25, after 3 ticks


def test_particles_removed_when_expired() -> None:
    g = _make_game()
    p = Particle(x=100, y=100, vx=0, vy=0, color=8, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text ──


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 80, "+10", 11)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+10"
    assert ft.color == 11
    assert ft.life > 0


def test_update_floating_texts() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 80, "TEST", 7)
    orig_y = g.floating_texts[0].y
    g._update_floating_texts()
    assert g.floating_texts[0].y < orig_y
    assert g.floating_texts[0].life == 29  # started at 30, minus 1


def test_floating_texts_removed_when_expired() -> None:
    g = _make_game()
    ft = FloatingText(x=100, y=80, text="DEAD", color=7, life=1)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Start playing ──


def test_start_playing() -> None:
    g = _make_game()
    g.score = 999
    g._start_playing()
    assert g.phase == Phase.PLAYING
    assert g.score == 0  # reset


# ── Game over restart ──


def test_game_over_restart() -> None:
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    g._update_game_over({"space": False, "space_p": True})
    assert g.phase == Phase.TITLE
    assert g.score == 0


def test_game_over_no_press() -> None:
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    g._update_game_over({"space": False, "space_p": False})
    assert g.phase == Phase.GAME_OVER


# ── is_super utility ──


def test_is_super() -> None:
    g = _make_game()
    assert g._is_super() is False
    g.super_mode = True
    assert g._is_super() is True


# ── Headless input safety ──


def test_get_input_headless() -> None:
    g = _make_game()
    inp = g._get_input()
    assert inp == {"space": False, "space_p": False}


# ── Deterministic RNG ──


def test_seeded_rng_deterministic() -> None:
    g1 = _make_game(42)
    g2 = _make_game(42)
    g1._spawn_hurdle()
    g2._spawn_hurdle()
    assert g1.hurdles[0].x == g2.hurdles[0].x
    assert g1.hurdles[0].color == g2.hurdles[0].color


# ── Super activation at threshold ──


def test_super_activation_exact_threshold() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1
    _place_hurdle_at_player(g)
    g.player_y = HURDLE_Y - 5
    g.player_on_ground = False
    g._check_hurdle_clear()
    assert g.super_mode is True


def test_no_double_super_activation() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.combo = COMBO_THRESHOLD + 2
    g._check_super_activation()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION  # unchanged


# ── Hurdle already scored — skip ──


def test_already_scored_hurdle_skipped() -> None:
    g = _make_game()
    h = _place_hurdle_at_player(g)
    h.scored = True
    g.player_y = HURDLE_Y - 5
    g.player_on_ground = False
    prev_combo = g.combo
    g._check_hurdle_clear()
    assert g.combo == prev_combo  # no change
