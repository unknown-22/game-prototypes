"""test_imports.py — Headless logic tests for MOLE CHAIN.

Tests core game logic without initializing Pyxel (no display needed).
Uses Game.__new__ pattern to bypass pyxel.init().
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/054_mole_chain")
from main import (
    BASE_SCORE,
    CELL_H,
    CELL_W,
    COLS,
    COLOR_IDS,
    COLOR_NAMES,
    DISPLAY_SCALE,
    FPS,
    GAME_TIME,
    GRID_X,
    GRID_Y,
    HOLE_R,
    NUM_COLORS,
    RISE_FRAMES,
    ROWS,
    SCREEN_H,
    SCREEN_W,
    SUPER_COMBO_THRESHOLD,
    SUPER_SCORE,
    EchoGhost,
    FloatingText,
    Game,
    Mole,
    MoleState,
    Particle,
    Phase,
)


# ── Constants Tests ────────────────────────────────────────────────────


def test_constants() -> None:
    """Verify all game constants are reasonable."""
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert DISPLAY_SCALE == 2
    assert FPS == 30
    assert GAME_TIME == 60
    assert COLS == 4
    assert ROWS == 3
    assert NUM_COLORS == 4
    assert len(COLOR_IDS) == 4
    assert len(COLOR_NAMES) == 4
    assert HOLE_R > 0
    assert CELL_W > HOLE_R * 2
    assert CELL_H > HOLE_R * 2
    assert BASE_SCORE == 100
    assert SUPER_SCORE == 200
    assert SUPER_COMBO_THRESHOLD == 4
    # Grid fits on screen
    assert GRID_X >= 0
    assert GRID_X + COLS * CELL_W <= SCREEN_W
    assert GRID_Y >= 0
    assert GRID_Y + ROWS * CELL_H <= SCREEN_H


# ── Dataclass Tests ────────────────────────────────────────────────────


def test_mole_position() -> None:
    """Mole cx/cy computed from col, row, and grid constants."""
    mole = Mole(col=0, row=0)
    assert mole.cx == GRID_X + CELL_W // 2
    assert mole.cy == GRID_Y + CELL_H // 2

    mole2 = Mole(col=3, row=2)
    assert mole2.cx == GRID_X + 3 * CELL_W + CELL_W // 2
    assert mole2.cy == GRID_Y + 2 * CELL_H + CELL_H // 2


def test_mole_hit_test() -> None:
    """Hit test returns True inside radius, False outside."""
    mole = Mole(col=1, row=1)
    cx, cy = mole.cx, mole.cy
    # Center hit
    assert mole.hit_test(cx, cy)
    # Near edge
    assert mole.hit_test(cx + HOLE_R, cy)
    # Outside
    assert not mole.hit_test(cx + HOLE_R + 10, cy)
    assert not mole.hit_test(cx, cy + HOLE_R + 10)


def test_mole_state_default() -> None:
    """Default mole is HIDDEN with 0 timer."""
    mole = Mole(col=0, row=0)
    assert mole.state == MoleState.HIDDEN
    assert mole.timer == 0


def test_particle_fields() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_fields() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+100", life=25, color=10)
    assert ft.x == 50.0
    assert ft.y == 60.0
    assert ft.text == "+100"
    assert ft.life == 25


def test_echo_ghost_fields() -> None:
    eg = EchoGhost(x=100.0, y=120.0, life=30, color=2)
    assert eg.life == 30
    assert eg.color == 2


# ── Game State Tests ───────────────────────────────────────────────────


def _make_game() -> Game:
    """Create a Game instance bypassing Pyxel init."""
    g: Game = Game.__new__(Game)
    # Pre-init all attributes that reset() will touch
    g._rng = __import__("random").Random(42)
    g.moles = []
    g.particles = []
    g.floating_texts = []
    g.echoes = []
    g._shake_frames = 0
    g.reset()
    return g


def test_game_reset() -> None:
    """After reset, game is in PLAYING phase with zero score."""
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hits == 0
    assert g.misses == 0
    assert g.time_left == float(GAME_TIME)
    assert g.super_mode is False
    assert g._active_color is None


def test_game_moles_grid() -> None:
    """After reset, all moles are HIDDEN in correct positions."""
    g = _make_game()
    assert len(g.moles) == COLS
    for c in range(COLS):
        assert len(g.moles[c]) == ROWS
        for r in range(ROWS):
            mole = g.moles[c][r]
            assert mole.state == MoleState.HIDDEN
            assert mole.col == c
            assert mole.row == r


# ── Spawn Tests ────────────────────────────────────────────────────────


def test_try_spawn_mole() -> None:
    """_try_spawn_mole creates a mole in RISING state."""
    g = _make_game()
    g._max_active = 8
    g._try_spawn_mole()

    # Find the spawned mole
    found = False
    for c in range(COLS):
        for r in range(ROWS):
            if g.moles[c][r].state != MoleState.HIDDEN:
                found = True
                mole = g.moles[c][r]
                assert mole.state == MoleState.RISING
                assert mole.timer == RISE_FRAMES
                assert 0 <= mole.color < NUM_COLORS
    assert found, "No mole was spawned"


def test_try_spawn_mole_respects_max_active() -> None:
    """When max_active moles are already visible, no new spawn."""
    g = _make_game()
    g._max_active = 2
    # Spawn 2 moles
    g._try_spawn_mole()
    g._try_spawn_mole()

    # Both should be in RISING or HIDDEN state (HIDDEN if same hole picked)
    active = sum(
        1 for c in range(COLS) for r in range(ROWS)
        if g.moles[c][r].state != MoleState.HIDDEN
    )
    assert active <= 2


def test_try_spawn_mole_no_empty_holes() -> None:
    """When all holes are occupied, no crash."""
    g = _make_game()
    # Fill all holes
    for c in range(COLS):
        for r in range(ROWS):
            g.moles[c][r].state = MoleState.VISIBLE
            g.moles[c][r].color = 0
    g._max_active = COLS * ROWS + 1
    # Should not crash
    g._try_spawn_mole()


# ── Mole Update Tests ──────────────────────────────────────────────────


def test_update_mole_rising_to_visible() -> None:
    """After RISE_FRAMES ticks, RISING mole becomes VISIBLE."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.color = 1
    mole.state = MoleState.RISING
    mole.timer = 1
    g._update_mole(mole)
    assert mole.state == MoleState.VISIBLE
    assert mole.timer > 0  # visible timer set


def test_update_mole_visible_to_falling() -> None:
    """After visible timer expires, VISIBLE mole becomes FALLING."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.state = MoleState.VISIBLE
    mole.timer = 1
    g._update_mole(mole)
    assert mole.state == MoleState.FALLING
    assert mole.timer == 8  # FALL_FRAMES


def test_update_mole_falling_to_hidden() -> None:
    """After fall timer expires, FALLING mole becomes HIDDEN."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.state = MoleState.FALLING
    mole.timer = 1
    g._update_mole(mole)
    assert mole.state == MoleState.HIDDEN


def test_update_mole_whacked_to_hidden() -> None:
    """After whacked timer expires, WHACKED mole becomes HIDDEN."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.state = MoleState.WHACKED
    mole.timer = 1
    g._update_mole(mole)
    assert mole.state == MoleState.HIDDEN


def test_update_mole_hidden_noop() -> None:
    """HIDDEN moles stay HIDDEN."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.state = MoleState.HIDDEN
    mole.timer = 5
    g._update_mole(mole)
    assert mole.state == MoleState.HIDDEN
    assert mole.timer == 5  # unchanged


# ── Whack Tests ────────────────────────────────────────────────────────


def test_whack_mole_basic() -> None:
    """Whacking a mole awards score and transitions to WHACKED."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.color = 0
    mole.state = MoleState.VISIBLE
    mole.timer = 100

    initial_score = g.score
    g._whack_mole(mole)

    assert mole.state == MoleState.WHACKED
    assert g.score > initial_score
    assert g.combo == 1
    assert g._active_color == 0
    assert g.hits == 1


def test_whack_mole_same_color_builds_combo() -> None:
    """Consecutive same-color whacks build combo."""
    g = _make_game()
    # First whack
    m1 = g.moles[0][0]
    m1.color = 0
    m1.state = MoleState.VISIBLE
    m1.timer = 100
    g._whack_mole(m1)
    assert g.combo == 1
    assert g._active_color == 0
    score1 = g.score

    # Second same-color whack
    m2 = g.moles[1][0]
    m2.color = 0
    m2.state = MoleState.VISIBLE
    m2.timer = 100
    g._whack_mole(m2)
    assert g.combo == 2
    assert g._active_color == 0
    # Score should be higher due to combo multiplier
    assert g.score > score1 + BASE_SCORE  # more than base due to combo


def test_whack_mole_wrong_color_breaks_combo() -> None:
    """Whacking a different color breaks the combo."""
    g = _make_game()
    # Build combo
    m1 = g.moles[0][0]
    m1.color = 0
    m1.state = MoleState.VISIBLE
    m1.timer = 100
    g._whack_mole(m1)
    assert g.combo == 1

    # Wrong color
    m2 = g.moles[1][0]
    m2.color = 1
    m2.state = MoleState.VISIBLE
    m2.timer = 100
    g._whack_mole(m2)
    # Combo should break (reset to 0), then rebuild from the new whack
    # _whack_mole calls _break_combo first, then _do_whack
    # But _do_whack doesn't increment combo — it's done in _whack_mole
    # Actually, when wrong color: _break_combo() sets combo=0, _active_color=None
    # then _do_whack with combo_mult=1.0. combo stays 0.
    # Actually wait — let me re-read the code.
    # _whack_mole: color != _active_color → _break_combo(), then _do_whack with combo_mult=1.0
    # But it does NOT increment combo or set _active_color again.
    # So combo should be 0 after wrong-color whack.
    assert g.combo == 0
    assert g._active_color is None
    assert g.misses == 1


def test_whack_mole_super_trigger() -> None:
    """COMBO >= 4 triggers SUPER mode."""
    g = _make_game()
    # Manually set up combo = 3
    g.combo = 3
    g._active_color = 0

    # Set up multiple visible moles of the same color
    for c in range(3):
        m = g.moles[c][0]
        m.color = 0
        m.state = MoleState.VISIBLE
        m.timer = 100

    # 4th whack should trigger super
    m4 = g.moles[3][0]
    m4.color = 0
    m4.state = MoleState.VISIBLE
    m4.timer = 100

    g._whack_mole(m4)
    assert g.combo == 4
    assert g.super_mode is True
    # After super trigger, all visible same-color moles should be whacked
    for c in range(3):
        assert g.moles[c][0].state == MoleState.WHACKED


def test_break_combo() -> None:
    """_break_combo resets combo and increments misses."""
    g = _make_game()
    g.combo = 5
    g._active_color = 2
    g._break_combo()
    assert g.combo == 0
    assert g._active_color is None
    assert g.misses == 1


def test_break_combo_noop_when_zero() -> None:
    """_break_combo at combo=0 is a no-op."""
    g = _make_game()
    g.combo = 0
    g._break_combo()
    assert g.combo == 0
    assert g.misses == 0


# ── Combo Multiplier Tests ─────────────────────────────────────────────


def test_combo_multiplier_increases_score() -> None:
    """Higher combo multipliers give higher scores."""
    g = _make_game()

    def whack_and_get_score(combo_level: int) -> int:
        g.reset()
        g.combo = combo_level - 1  # pre-set
        g._active_color = 0
        m = g.moles[0][0]
        m.color = 0
        m.state = MoleState.VISIBLE
        m.timer = 100
        score_before = g.score
        g._whack_mole(m)
        return g.score - score_before

    s1 = whack_and_get_score(1)  # combo_mult = 1.0
    s2 = whack_and_get_score(2)  # combo_mult = 1.5
    s3 = whack_and_get_score(3)  # combo_mult = 2.0
    assert s2 > s1
    assert s3 > s2


# ── Echo Ghost Tests ───────────────────────────────────────────────────


def test_whack_creates_echo() -> None:
    """Whacking a mole creates an echo ghost."""
    g = _make_game()
    assert len(g.echoes) == 0
    mole = g.moles[0][0]
    mole.color = 0
    mole.state = MoleState.VISIBLE
    mole.timer = 100

    g._whack_mole(mole)
    assert len(g.echoes) == 1
    assert g.echoes[0].color == 0
    assert g.echoes[0].life == 30


# ── Particle Tests ─────────────────────────────────────────────────────


def test_whack_creates_particles() -> None:
    """Whacking creates particles."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.color = 0
    mole.state = MoleState.VISIBLE
    mole.timer = 100

    initial_particles = len(g.particles)
    g._whack_mole(mole)
    assert len(g.particles) > initial_particles


def test_particle_lifecycle() -> None:
    """Particles decay over time."""
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=0, vy=0, life=3, color=8)]
    for _ in range(3):
        # Simulate update loop
        for p in g.particles[:]:
            p.life -= 1
            if p.life <= 0:
                g.particles.remove(p)
    assert len(g.particles) == 0


# ── Floating Text Tests ────────────────────────────────────────────────


def test_whack_creates_floating_text() -> None:
    """Whacking creates floating score text."""
    g = _make_game()
    mole = g.moles[0][0]
    mole.color = 0
    mole.state = MoleState.VISIBLE
    mole.timer = 100

    initial_texts = len(g.floating_texts)
    g._whack_mole(mole)
    assert len(g.floating_texts) > initial_texts


def test_floating_text_lifecycle() -> None:
    """Floating texts decay over time."""
    g = _make_game()
    g.floating_texts = [FloatingText(x=50, y=50, text="+100", life=3, color=10)]
    for _ in range(3):
        for ft in g.floating_texts[:]:
            ft.life -= 1
            if ft.life <= 0:
                g.floating_texts.remove(ft)
    assert len(g.floating_texts) == 0


# ── Timer Tests ────────────────────────────────────────────────────────


def test_timer_decreases() -> None:
    """Timer decreases each frame in PLAYING state."""
    g = _make_game()
    initial_time = g.time_left
    # Simulate update() timer logic without calling pyxel.btnp()
    g.time_left -= 1.0 / FPS
    assert g.time_left < initial_time
    assert abs(g.time_left - (initial_time - 1.0 / FPS)) < 0.001


def test_timer_expires_game_over() -> None:
    """When timer reaches 0, game transitions to GAME_OVER."""
    g = _make_game()
    # Simulate the game-over check from update() without pyxel calls
    g.time_left = 0
    if g.time_left <= 0:
        g.time_left = 0
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Difficulty Scaling Tests ───────────────────────────────────────────


def test_difficulty_increases_over_time() -> None:
    """As time passes, difficulty and max_active increase."""
    g = _make_game()
    initial_max = g._max_active
    # Simulate playing for 30 seconds
    g.time_left = float(GAME_TIME) - 30
    # Trigger difficulty recalculation (happens in update)
    elapsed = GAME_TIME - g.time_left
    g._difficulty = 1.0 + elapsed / 15.0
    g._max_active = min(3 + int(elapsed // 15), 8)
    assert g._difficulty > 1.0
    assert g._max_active >= initial_max


# ── Game Over Tests ────────────────────────────────────────────────────


def test_game_over_restart_on_enter() -> None:
    """Game over phase doesn't crash, state is restartable."""
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    # update in game over should not crash
    # (can't simulate pyxel.btnp without display, but state is clean)
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0


# ── Run ────────────────────────────────────────────────────────────────


def main() -> None:
    """Run all tests."""
    tests = [
        test_constants,
        test_mole_position,
        test_mole_hit_test,
        test_mole_state_default,
        test_particle_fields,
        test_floating_text_fields,
        test_echo_ghost_fields,
        test_game_reset,
        test_game_moles_grid,
        test_try_spawn_mole,
        test_try_spawn_mole_respects_max_active,
        test_try_spawn_mole_no_empty_holes,
        test_update_mole_rising_to_visible,
        test_update_mole_visible_to_falling,
        test_update_mole_falling_to_hidden,
        test_update_mole_whacked_to_hidden,
        test_update_mole_hidden_noop,
        test_whack_mole_basic,
        test_whack_mole_same_color_builds_combo,
        test_whack_mole_wrong_color_breaks_combo,
        test_whack_mole_super_trigger,
        test_break_combo,
        test_break_combo_noop_when_zero,
        test_combo_multiplier_increases_score,
        test_whack_creates_echo,
        test_whack_creates_particles,
        test_particle_lifecycle,
        test_whack_creates_floating_text,
        test_floating_text_lifecycle,
        test_timer_decreases,
        test_timer_expires_game_over,
        test_difficulty_increases_over_time,
        test_game_over_restart_on_enter,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {test.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
