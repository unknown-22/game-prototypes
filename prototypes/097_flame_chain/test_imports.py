from __future__ import annotations

import random

import main as _main_module


def _new_game(seed: int = 42) -> _main_module.Game:
    """Create a Game in headless mode (bypassing pyxel.init/run)."""
    game = _main_module.Game.__new__(_main_module.Game)
    game.rng = random.Random(seed)
    game.particles = []
    game.grid = [[None] * _main_module.GRID_COLS for _ in range(_main_module.GRID_ROWS)]
    game.flame_color = _main_module.RED
    game.combo = 0
    game.max_combo = 0
    game.score = 0
    game.hp = _main_module.MAX_HP
    game.super_timer = 0
    game.spawn_timer = 0
    game.super_active = False
    game.reset()
    return game


# ---------------------------------------------------------------------------
# Import / symbol tests
# ---------------------------------------------------------------------------


def test_all_symbols_importable() -> None:
    names = [
        "Phase",
        "Game",
        "App",
        "Ingredient",
        "Particle",
        "SCREEN_W",
        "SCREEN_H",
        "GRID_COLS",
        "GRID_ROWS",
        "MAX_HP",
        "SUPER_COMBO_THRESHOLD",
        "SUPER_DURATION",
        "INGREDIENT_TIMER_MAX",
        "BASE_SCORE",
    ]
    for name in names:
        assert hasattr(_main_module, name), f"Missing symbol: {name}"


def test_enum_phases() -> None:
    assert _main_module.Phase.TITLE is not None
    assert _main_module.Phase.PLAYING is not None
    assert _main_module.Phase.GAME_OVER is not None
    assert len(list(_main_module.Phase)) == 3


def test_constants() -> None:
    assert _main_module.SCREEN_W == 320
    assert _main_module.SCREEN_H == 240
    assert _main_module.GRID_COLS == 4
    assert _main_module.GRID_ROWS == 3
    assert _main_module.MAX_HP == 5
    assert _main_module.SUPER_COMBO_THRESHOLD == 5
    assert _main_module.SUPER_DURATION == 300
    assert _main_module.INGREDIENT_TIMER_MAX == 180
    assert _main_module.BASE_SCORE == 100


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


def test_reset_initial_state() -> None:
    game = _new_game()
    assert game.phase == _main_module.Phase.TITLE
    assert game.combo == 0
    assert game.max_combo == 0
    assert game.score == 0
    assert game.hp == _main_module.MAX_HP
    assert game.super_active is False
    assert game.super_timer == 0
    assert game.spawn_timer == 0
    assert game.particles == []
    for row in range(_main_module.GRID_ROWS):
        for col in range(_main_module.GRID_COLS):
            assert game.grid[row][col] is None


def test_reset_clears_all() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.score = 500
    game.combo = 3
    game.max_combo = 5
    game.hp = 2
    game.super_active = True
    game.super_timer = 100
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game.particles = [
        _main_module.Particle(x=10, y=10, vx=1, vy=1, life=5, color=_main_module.WHITE)
    ]
    game.reset()
    assert game.score == 0
    assert game.combo == 0
    assert game.max_combo == 0
    assert game.hp == _main_module.MAX_HP
    assert game.super_active is False
    assert game.super_timer == 0
    assert game.particles == []
    for row in range(_main_module.GRID_ROWS):
        for col in range(_main_module.GRID_COLS):
            assert game.grid[row][col] is None


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------


def test_grid_click_to_cell_valid() -> None:
    game = _new_game()
    result = game._grid_click_to_cell(
        _main_module.GRID_X + 10, _main_module.GRID_Y + 10
    )
    assert result == (0, 0)


def test_grid_click_to_cell_invalid() -> None:
    game = _new_game()
    result = game._grid_click_to_cell(5, 5)
    assert result is None


def test_grid_click_to_cell_last() -> None:
    game = _new_game()
    x = _main_module.GRID_X + 3 * _main_module.CELL_W + 10
    y = _main_module.GRID_Y + 2 * _main_module.CELL_H + 10
    result = game._grid_click_to_cell(x, y)
    assert result == (3, 2)


# ---------------------------------------------------------------------------
# _cook — empty cell
# ---------------------------------------------------------------------------


def test_cook_empty_cell_returns_false() -> None:
    game = _new_game()
    assert game._cook(0, 0) is False


# ---------------------------------------------------------------------------
# _cook — matching color
# ---------------------------------------------------------------------------


def test_cook_matching_color_sets_combo() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    result = game._cook(0, 0)
    assert result is True
    assert game.combo == 1
    assert game.score == _main_module.BASE_SCORE * 1  # base * combo * 1
    assert game.grid[0][0] is None


def test_cook_matching_color_increments_combo() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.combo = 2
    game.score = 200
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    result = game._cook(0, 0)
    assert result is True
    assert game.combo == 3
    assert game.score == 200 + _main_module.BASE_SCORE * 3
    assert game.grid[0][0] is None


def test_cook_updates_flame_color() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.combo = 1
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    result = game._cook(0, 0)
    assert result is True
    assert game.flame_color == _main_module.RED
    assert game.combo == 2


# ---------------------------------------------------------------------------
# _cook — non-matching color (burn)
# ---------------------------------------------------------------------------


def test_cook_wrong_color_resets_combo() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.combo = 4
    game.max_combo = 4
    game.score = 1000
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.LIME, x=0, y=0, timer=100
    )
    result = game._cook(0, 0)
    assert result is False
    assert game.combo == 0
    assert game.hp == _main_module.MAX_HP - 1
    assert game.grid[0][0] is None


# ---------------------------------------------------------------------------
# _cook — super mode (all colors accepted)
# ---------------------------------------------------------------------------


def test_cook_super_mode_any_color_accepted() -> None:
    game = _new_game()
    game.super_active = True
    game.flame_color = _main_module.RED
    game.combo = 5
    game.score = 0
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.LIGHT_BLUE, x=0, y=0, timer=100
    )
    result = game._cook(0, 0)
    assert result is True
    assert game.combo == 6
    # 3x score in super
    assert game.score == _main_module.BASE_SCORE * 6 * 3
    # Flame updates to cooked color
    assert game.flame_color == _main_module.LIGHT_BLUE


def test_cook_super_mode_3x_score() -> None:
    game = _new_game()
    game.super_active = True
    game.flame_color = _main_module.RED
    game.combo = 2
    game.score = 0
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game._cook(0, 0)
    assert game.score == _main_module.BASE_SCORE * 3 * 3


# ---------------------------------------------------------------------------
# COMBO logic
# ---------------------------------------------------------------------------


def test_max_combo_tracked() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.combo = 3
    game.max_combo = 3
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game._cook(0, 0)
    assert game.max_combo == 4


def test_max_combo_not_lost_on_wrong_color() -> None:
    game = _new_game()
    game.combo = 5
    game.max_combo = 5
    game.flame_color = _main_module.RED
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.LIME, x=0, y=0, timer=100
    )
    game._cook(0, 0)
    assert game.combo == 0
    assert game.max_combo == 5


def test_score_formula_first_cook() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.combo = 0
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game._cook(0, 0)
    assert game.score == _main_module.BASE_SCORE * 1


# ---------------------------------------------------------------------------
# SUPER DISH activation / deactivation
# ---------------------------------------------------------------------------


def test_super_activates_at_combo_5() -> None:
    game = _new_game()
    game.flame_color = _main_module.RED
    game.combo = 4
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game._cook(0, 0)
    assert game.combo == 5
    assert game.super_active is True
    assert game.super_timer == _main_module.SUPER_DURATION


def test_super_deactivates_after_timer() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.super_active = True
    game.super_timer = 1
    game.combo = 8
    game.update()
    assert game.super_active is False
    assert game.combo == 0


def test_super_not_re_activated_during_super() -> None:
    """Super mode should not reset timer when already active."""
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.super_active = True
    game.super_timer = 200
    game.combo = 4
    game.flame_color = _main_module.RED
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game._cook(0, 0)
    assert game.super_active is True
    assert game.super_timer == 200  # Not reset


# ---------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------


def test_spawn_fills_empty_slot() -> None:
    game = _new_game()
    # Grid is empty, so spawn should succeed
    result = game._spawn_ingredient()
    assert result is True
    filled = 0
    for row in range(_main_module.GRID_ROWS):
        for col in range(_main_module.GRID_COLS):
            if game.grid[row][col] is not None:
                filled += 1
    assert filled == 1


def test_spawn_fails_when_grid_full() -> None:
    game = _new_game()
    for row in range(_main_module.GRID_ROWS):
        for col in range(_main_module.GRID_COLS):
            game.grid[row][col] = _main_module.Ingredient(
                color=_main_module.RED, x=col, y=row, timer=100
            )
    result = game._spawn_ingredient()
    assert result is False


# ---------------------------------------------------------------------------
# Timer / expiration
# ---------------------------------------------------------------------------


def test_timers_decrement() -> None:
    game = _new_game()
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=10
    )
    game._update_timers()
    assert game.grid[0][0] is not None
    assert game.grid[0][0].timer == 9  # type: ignore[union-attr]


def test_timer_expiration_loses_hp() -> None:
    game = _new_game()
    game.hp = 5
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=1
    )
    game._update_timers()
    assert game.grid[0][0] is None
    assert game.hp == 4


def test_timer_does_not_reset_combo() -> None:
    game = _new_game()
    game.combo = 3
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=1
    )
    game._update_timers()
    assert game.grid[0][0] is None
    assert game.combo == 3  # Combo unaffected by expiration


# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------


def test_spawn_particles_adds_to_list() -> None:
    game = _new_game()
    assert len(game.particles) == 0
    game._spawn_particles(100, 100, _main_module.RED, 5)
    assert len(game.particles) == 5


def test_particle_life_decrements() -> None:
    game = _new_game()
    p = _main_module.Particle(x=10, y=10, vx=1, vy=1, life=5, color=_main_module.WHITE)
    game.particles = [p]
    game._update_particles()
    assert len(game.particles) == 1
    assert game.particles[0].life == 4


def test_particle_removed_when_life_zero() -> None:
    game = _new_game()
    p = _main_module.Particle(x=10, y=10, vx=1, vy=1, life=1, color=_main_module.WHITE)
    game.particles = [p]
    game._update_particles()
    assert len(game.particles) == 0


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------


def test_game_over_when_hp_zero() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.hp = 0
    game.update()
    assert game.phase == _main_module.Phase.GAME_OVER


def test_game_over_when_hp_below_zero() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.hp = -1
    game.update()
    assert game.phase == _main_module.Phase.GAME_OVER


def test_no_game_over_while_hp_positive() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.hp = 1
    game.update()
    assert game.phase == _main_module.Phase.PLAYING


# ---------------------------------------------------------------------------
# update() phase guard
# ---------------------------------------------------------------------------


def test_update_noop_in_title() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.TITLE
    game.hp = 0
    game.update()
    assert game.phase == _main_module.Phase.TITLE


def test_update_noop_in_game_over() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.GAME_OVER
    spawn_before = game.spawn_timer
    game.update()
    assert game.spawn_timer == spawn_before


# ---------------------------------------------------------------------------
# handle_click
# ---------------------------------------------------------------------------


def test_handle_click_noop_in_title() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.TITLE
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game.handle_click(
        _main_module.GRID_X + 10, _main_module.GRID_Y + 10
    )
    assert game.grid[0][0] is not None  # Not cooked


def test_handle_click_cooks_in_playing() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.flame_color = _main_module.RED
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game.handle_click(
        _main_module.GRID_X + 10, _main_module.GRID_Y + 10
    )
    assert game.grid[0][0] is None


def test_handle_click_outside_grid() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.flame_color = _main_module.RED
    game.grid[0][0] = _main_module.Ingredient(
        color=_main_module.RED, x=0, y=0, timer=100
    )
    game.handle_click(5, 5)
    assert game.grid[0][0] is not None


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


def test_ingredient_dataclass() -> None:
    ing = _main_module.Ingredient(color=_main_module.RED, x=1, y=2, timer=100)
    assert ing.color == _main_module.RED
    assert ing.x == 1
    assert ing.y == 2
    assert ing.timer == 100
    assert ing.opacity == 1.0


def test_particle_dataclass() -> None:
    p = _main_module.Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=10, color=_main_module.WHITE)
    assert p.x == 1.5
    assert p.y == 2.5
    assert p.vx == 0.5
    assert p.vy == -0.5
    assert p.life == 10
    assert p.color == _main_module.WHITE
    assert p.size == 2
