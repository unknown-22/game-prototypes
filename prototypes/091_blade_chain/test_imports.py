"""Basic import verification for 091_blade_chain."""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import main


def _make_game() -> main.Game:
    """Create a Game instance bypassing __init__ (no pyxel.init/run)."""
    game = main.Game.__new__(main.Game)
    # Pre-init all instance attributes
    game._rng = random.Random(42)
    game.reset()
    return game


def test_import_and_reset() -> None:
    """Verify module imports and reset initializes all state correctly."""
    game = _make_game()
    assert game.phase == main.Phase.TITLE
    assert game.score == 0
    assert game.timer == main.MATCH_DURATION
    assert game.combo == 0
    assert game.max_combo == 0
    assert game.heat == 0
    assert game.player.x == 60.0
    assert game.player.y == 120.0
    assert game.ai.x == 260.0
    assert game.ai.y == 120.0
    assert game.player_color == 0
    assert game.last_player_color is None
    assert game.echoes == []
    assert game.particles == []
    assert game.floats == []
    assert game.shake_frames == 0
    assert not game.super_lunge_active


def test_is_blade_hitting() -> None:
    """Test the pure blade-hit detection function."""
    # Direct hit — target at end of blade
    assert main.Game._is_blade_hitting(0, 0, 0, 60, 0, 12, 60)
    # Miss — target too far
    assert not main.Game._is_blade_hitting(0, 0, 0, 200, 0, 12, 60)
    # Edge hit — blade passes near target
    assert main.Game._is_blade_hitting(0, 0, 0, 30, 10, 12, 60)
    # Target behind lunger (distance to blade start > radius)
    assert not main.Game._is_blade_hitting(0, 0, 0, -20, 0, 12, 60)


def test_swap_color() -> None:
    """Test blade color cycling."""
    game = _make_game()
    assert game.player_color == 0
    game._swap_color(1)
    assert game.player_color == 1
    game._swap_color(1)
    assert game.player_color == 2
    game._swap_color(1)
    assert game.player_color == 3
    game._swap_color(1)
    assert game.player_color == 0  # wraps around
    game._swap_color(-1)
    assert game.player_color == 3  # wraps backward


def test_compute_combo_first_hit() -> None:
    """Test first hit sets combo to 1."""
    game = _make_game()
    result = game._compute_combo(main.RED)
    assert result == 1
    assert game.combo == 1
    assert game.last_player_color == main.RED
    assert not game.super_lunge_active


def test_compute_combo_builds_super() -> None:
    """Test building combo to SUPER LUNGE threshold."""
    game = _make_game()
    for i in range(4):
        result = game._compute_combo(main.RED)
    assert result == 4
    assert game.combo == 4
    assert game.super_lunge_active


def test_compute_combo_resets_on_wrong_color() -> None:
    """Test combo resets when color changes."""
    game = _make_game()
    game._compute_combo(main.RED)
    game._compute_combo(main.RED)  # combo = 2
    assert game.combo == 2
    result = game._compute_combo(main.GREEN)  # different color
    assert result == 1
    assert game.combo == 1
    assert not game.super_lunge_active


def test_check_lunge_hit() -> None:
    """Test lunge hit detection between fencers."""
    game = _make_game()
    # Player lunges straight right, AI is at (260, 120) — too far
    assert not game._check_lunge_hit(game.player, game.ai, 0.0)
    # Move AI close
    game.ai.x = 100.0
    game.ai.y = 120.0
    assert game._check_lunge_hit(game.player, game.ai, 0.0)


def test_lunge_hit_scoring() -> None:
    """Test _lunge applies damage, score, particles, and combo."""
    game = _make_game()
    game.phase = main.Phase.PLAYING
    game._rng = random.Random(42)
    # Place AI in lunge path
    game.ai.x = 100.0
    game.ai.y = 120.0
    game.lunge_angle = 0.0
    game.lunge_start_x = game.player.x
    game.lunge_start_y = game.player.y
    game.player_color = 0  # RED

    hit, hit_type = game._lunge()
    assert hit
    assert hit_type == "HIT"
    assert game.combo == 1
    assert game.score > 0
    assert len(game.particles) > 0
    assert len(game.floats) == 1


def test_lunge_miss() -> None:
    """Test _lunge on miss resets combo."""
    game = _make_game()
    game._rng = random.Random(42)
    game.combo = 3
    game.lunge_angle = math.atan2(-1, 0)  # straight up (away from AI)
    game.lunge_start_x = game.player.x
    game.lunge_start_y = game.player.y

    hit, hit_type = game._lunge()
    assert not hit
    assert hit_type == "MISS"
    assert game.combo == 0
    assert not game.super_lunge_active


def test_super_lunge() -> None:
    """Test super lunge triggers at combo >= 4."""
    game = _make_game()
    game._rng = random.Random(42)
    game.combo = 3
    game.last_player_color = main.RED
    game.player_color = 0

    # Place AI in path
    game.ai.x = 100.0
    game.ai.y = 120.0
    game.lunge_angle = 0.0
    game.lunge_start_x = game.player.x
    game.lunge_start_y = game.player.y

    hit, hit_type = game._lunge()
    assert hit
    assert hit_type == "SUPER"
    assert game.combo == 4
    assert game.super_lunge_active
    assert game.shake_frames == main.SHAKE_FRAMES


def test_echoes_update_and_cleanup() -> None:
    """Test echoes are added and cleaned up."""
    game = _make_game()
    game._add_echo(100, 100, 0.0, main.CYAN)
    assert len(game.echoes) == 1
    game.echoes[0].life = 1
    game._update_echoes()
    assert len(game.echoes) == 1  # life 0 after decrement
    game._update_echoes()
    assert len(game.echoes) == 0  # removed when life <= 0


def test_particles_update_and_cleanup() -> None:
    """Test particles move and are cleaned up."""
    game = _make_game()
    game._rng = random.Random(42)
    game._add_particles(100, 100, 5, main.RED)
    assert len(game.particles) == 5
    game.particles[0].life = 1
    game._update_particles()
    game._update_particles()
    assert len(game.particles) < 5  # at least the one with life=1 is gone


def test_floats_update_and_cleanup() -> None:
    """Test floating text drifts up and is cleaned up."""
    game = _make_game()
    game._add_float(100, 100, "TEST", main.WHITE)
    assert len(game.floats) == 1
    old_y = game.floats[0].y
    game.floats[0].life = 1
    game._update_floats()
    assert game.floats[0].y == old_y - 1
    game._update_floats()
    assert len(game.floats) == 0


def test_reset_after_game() -> None:
    """Test full reset clears all state."""
    game = _make_game()
    game.score = 100
    game.combo = 5
    game.heat = 8
    game.echoes.append(main.Echo(0, 0, 0, 10, main.CYAN))
    game.particles.append(main.Particle(0, 0, 1, 1, 10, main.RED))
    game.floats.append(main.FloatingText(0, 0, "x", 10, main.WHITE))
    game.reset()
    assert game.score == 0
    assert game.combo == 0
    assert game.heat == 0
    assert game.echoes == []
    assert game.particles == []
    assert game.floats == []
    assert game.phase == main.Phase.TITLE


def test_heat_game_over_condition() -> None:
    """Test that heat=10 triggers game over."""
    game = _make_game()
    game.phase = main.Phase.PLAYING
    game.heat = 10
    game._update_playing()
    assert game.phase == main.Phase.GAME_OVER


def test_timer_game_over_condition() -> None:
    """Test that timer reaching 0 triggers game over."""
    game = _make_game()
    game.phase = main.Phase.PLAYING
    game.timer = 1
    game._update_playing()
    assert game.timer == 0
    assert game.phase == main.Phase.GAME_OVER


def test_ai_hit_increases_heat() -> None:
    """Test that AI hitting player increases heat."""
    game = _make_game()
    game._rng = random.Random(42)
    game.phase = main.Phase.AI_TURN
    game.ai_lunging = True
    game.ai_lunge_frame = 1
    game.ai.x = 110.0
    game.ai.y = 120.0
    game.ai_lunge_angle = math.atan2(
        game.player.y - game.ai.y,
        game.player.x - game.ai.x,
    )
    old_heat = game.heat
    game._update_ai_turn()
    assert game.heat == old_heat + 1
