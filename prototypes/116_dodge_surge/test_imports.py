from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    Ball,
    Game,
    Opponent,
    Phase,
    RED,
    GREEN,
    BLUE,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.opponents = []
    g.field_balls = []
    g.thrown_balls = []
    g.particles = []
    g.floating_texts = []
    g.reset()
    return g


def _alive_opp(game: Game, idx: int = 0) -> Opponent:
    game.opponents[idx].alive = True
    game.opponents[idx].respawn_timer = 0
    return game.opponents[idx]


def test_combo_increment_same_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp0 = _alive_opp(g, 0)
    opp0.color = RED
    g._handle_hit(0, RED)
    assert g.combo == 1
    g.opponents[0].alive = True
    g._handle_hit(0, RED)
    assert g.combo == 2


def test_combo_reset_different_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    _alive_opp(g, 1).color = GREEN
    g._handle_hit(0, RED)
    assert g.combo == 1
    g.opponents[1].alive = True
    g._handle_hit(1, GREEN)
    assert g.combo == 1


def test_super_mode_activation() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    for _ in range(4):
        g.opponents[0].alive = True
        g._handle_hit(0, RED)
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.combo = 2
    g._last_hit_color = RED
    _alive_opp(g, 0).color = GREEN
    g._handle_hit(0, RED)
    assert g.score == 300 + 3 * 75


def test_heat_increase_wrong_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    g._handle_hit(0, GREEN)
    assert g.heat == 2


def test_heat_increase_player_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0
    g._handle_player_hit()
    assert g.heat == 1


def test_hp_decrease_player_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.hp = 5
    g._handle_player_hit()
    assert g.hp == 4


def test_game_over_hp_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.hp = 0
    g._update_playing(0, headless=True)
    assert g.phase == Phase.GAME_OVER


def test_game_over_max_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = Game.MAX_HEAT
    g._update_playing(0, headless=True)
    assert g.phase == Phase.GAME_OVER


def test_game_over_timer_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 0
    g._update_playing(0, headless=True)
    assert g.phase == Phase.GAME_OVER


def test_opponent_respawn() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    g._handle_hit(0, RED)
    assert g.opponents[0].alive is False
    g.opponents[0].respawn_timer = 1
    g._update_opponents(1)
    assert g.opponents[0].alive is True


def test_ball_spawning() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    initial = len(g.field_balls)
    for _ in range(120):
        g._update_spawning(1)
    assert len(g.field_balls) > initial


def test_player_pickup() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_inventory = 0
    g.player_x = 160.0
    g.player_y = 200.0
    g.field_balls.append(Ball(162.0, 198.0, RED, 0.0, 0.0, "field"))
    g._update_field_balls()
    assert g.player_inventory == 1
    assert len(g.field_balls) == 0


def test_inventory_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_inventory = Game.MAX_INVENTORY
    g.player_x = 160.0
    g.player_y = 200.0
    g.field_balls.append(Ball(162.0, 198.0, RED, 0.0, 0.0, "field"))
    g._update_field_balls()
    assert g.player_inventory == Game.MAX_INVENTORY
    assert len(g.field_balls) == 1


def test_particle_creation_on_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    g._handle_hit(0, RED)
    assert len(g.particles) > 0


def test_floating_text_creation_on_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    g._handle_hit(0, RED)
    assert len(g.floating_texts) > 0


def test_score_calculation() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g._last_hit_color = RED
    _alive_opp(g, 0).color = RED
    g._handle_hit(0, RED)
    assert g.score == 100 + 4 * 25


def test_max_combo_tracking() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    for _ in range(3):
        g.opponents[0].alive = True
        g._handle_hit(0, RED)
    assert g.max_combo == 3
    g.opponents[0].alive = True
    g.opponents[0].color = GREEN
    g._handle_hit(0, GREEN)
    assert g.max_combo == 3
    assert g.combo == 1


def test_super_mode_duration() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode(1)
    assert g.super_mode is False
    assert g.combo == 0


def test_heat_decay() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 5
    g._heat_decay_timer = Game.HEAT_DECAY_INTERVAL - 1
    g._update_heat_decay(1)
    assert g.heat == 4


def test_heat_decay_min_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0
    g._heat_decay_timer = Game.HEAT_DECAY_INTERVAL - 1
    g._update_heat_decay(1)
    assert g.heat == 0


def test_field_ball_limit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    for _ in range(120 * (Game.MAX_FIELD_BALLS + 5)):
        g._update_spawning(1)
    assert len(g.field_balls) <= Game.MAX_FIELD_BALLS


def test_opponent_throw_creates_ball() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = g.opponents[0]
    opp.throw_timer = 1
    g.thrown_balls.clear()
    g._update_opponents(1)
    assert len(g.thrown_balls) > 0
    assert g.thrown_balls[0].owner == "opponent"


def test_reset_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 999
    g.combo = 5
    g.hp = 1
    g.heat = 9
    g.super_mode = True
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.hp == Game.MAX_HP
    assert g.heat == 0
    assert g.super_mode is False
    assert g.player_inventory == 3
    assert g.game_timer == Game.GAME_DURATION


def test_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    _alive_opp(g, 0).color = RED
    for _ in range(3):
        g.opponents[0].alive = True
        g._handle_hit(0, RED)
    assert g.combo == 3
    g.opponents[0].alive = True
    g.opponents[0].color = RED
    g._handle_hit(0, GREEN)
    assert g.combo == 0


def test_super_mode_any_color_hits() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.score = 0
    _alive_opp(g, 0).color = RED
    g._handle_hit(0, BLUE)
    assert g.score > 0
    assert g.opponents[0].alive is False


def test_player_throw_decreases_inventory() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_inventory = 2
    g.player_x = 160.0
    g.player_y = 200.0
    _alive_opp(g, 0)
    g._player_throw()
    assert g.player_inventory == 1
    assert len(g.thrown_balls) == 1


def test_player_throw_no_inventory() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_inventory = 0
    _alive_opp(g, 0)
    g._player_throw()
    assert g.player_inventory == 0
    assert len(g.thrown_balls) == 0


def test_opponent_movement_clamped() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = g.opponents[0]
    opp.x = 10.0
    opp.vx = -2.0
    g._update_opponents(1)
    assert opp.x >= 16.0


def test_super_mode_expires_combo_reset() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.combo = 5
    g._last_hit_color = RED
    g.super_timer = 1
    g._update_super_mode(1)
    assert g.super_mode is False
    assert g.combo == 0
    assert g._last_hit_color == -1


def test_handle_hit_dead_opponent_noop() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.opponents[0].alive = False
    score_before = g.score
    g._handle_hit(0, RED)
    assert g.score == score_before


def test_player_hit_shake_and_particles() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.particles.clear()
    g._handle_player_hit()
    assert g.shake_frames == 10
    assert len(g.particles) == 10


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
