"""Headless tests for 098_arrow_chain -- pure-logic coverage."""

from __future__ import annotations

import random
import sys

sys.path.insert(0, ".")

# ---------------------------------------------------------------------------
# Mock pyxel so `import pyxel` in main.py does not fail
# ---------------------------------------------------------------------------
import types as _types  # noqa: E402

_mock = _types.ModuleType("pyxel")
_mock.COLOR_BLACK = 0
_mock.COLOR_NAVY = 1
_mock.COLOR_PURPLE = 2
_mock.COLOR_GREEN = 3
_mock.COLOR_BROWN = 4
_mock.COLOR_DARK_BLUE = 5
_mock.COLOR_LIGHT_BLUE = 6
_mock.COLOR_WHITE = 7
_mock.COLOR_RED = 8
_mock.COLOR_ORANGE = 9
_mock.COLOR_YELLOW = 10
_mock.COLOR_LIME = 11
_mock.COLOR_CYAN = 12
_mock.COLOR_GRAY = 13
_mock.COLOR_PINK = 14
_mock.COLOR_PEACH = 15

# input keys
_mock.KEY_SPACE = 32
_mock.KEY_RETURN = 13
_mock.KEY_UP = 38
_mock.KEY_DOWN = 40
_mock.KEY_LEFT = 37
_mock.KEY_RIGHT = 39
_mock.KEY_ESCAPE = 27

_mock.MOUSE_BUTTON_LEFT = 0
_mock.MOUSE_BUTTON_RIGHT = 1

_mock.mouse_x = 0
_mock.mouse_y = 0
_mock.mouse_wheel = 0

def _btn(*_a: object) -> bool:
    return False

def _btnp(*_a: object) -> bool:
    return False

def _btnr(*_a: object) -> bool:
    return False

_mock.btn = _btn  # type: ignore[attr-defined]
_mock.btnp = _btnp  # type: ignore[attr-defined]
_mock.btnr = _btnr  # type: ignore[attr-defined]

# drawing stubs (no-ops)
def _noop(*_a: object, **_kw: object) -> None:
    pass

_mock.init = _noop  # type: ignore[attr-defined]
_mock.run = _noop  # type: ignore[attr-defined]
_mock.cls = _noop  # type: ignore[attr-defined]
_mock.circ = _noop  # type: ignore[attr-defined]
_mock.circb = _noop  # type: ignore[attr-defined]
_mock.line = _noop  # type: ignore[attr-defined]
_mock.rect = _noop  # type: ignore[attr-defined]
_mock.rectb = _noop  # type: ignore[attr-defined]
_mock.pset = _noop  # type: ignore[attr-defined]
_mock.text = _noop  # type: ignore[attr-defined]
_mock.load = _noop  # type: ignore[attr-defined]
_mock.mouse = _noop  # type: ignore[attr-defined]

sys.modules["pyxel"] = _mock

# now import modules under test
from main import (  # noqa: E402
    Arrow,
    COLORS,
    FloatingText,
    Game,
    GRAVITY,
    MAX_HEAT,
    MAX_TARGETS,
    MIN_ALIVE_TARGETS,
    Particle,
    Phase,
    SUPER_COMBO,
    Target,
)


# ---------------------------------------------------------------------------
# factory
# ---------------------------------------------------------------------------
def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._init_state()
    g._rng = random.Random(seed)
    return g


# -- phase / state --------------------------------------------------------

def test_phase_values() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE, "initial phase should be TITLE"


def test_reset_clears_state() -> None:
    g = make_game()
    g.score = 999
    g.combo = 10
    g.max_combo = 10
    g.heat = 4
    g.timer = 100
    g.arrow_color = 3
    g.super_timer = 50
    g.targets.append(
        Target(x=100, y=100, depth=0.5, color=0, radius=10, score_base=100)
    )
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, color=8, life=10, max_life=10))
    g.floating_texts.append(
        FloatingText(x=0, y=0, text="X", color=7, life=5)
    )
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.timer == 60 * 30
    assert g.arrow_color == 0
    assert g.super_timer == 0
    assert g.targets == []
    assert g.particles == []
    assert g.floating_texts == []


# -- spawning ------------------------------------------------------------

def test_spawn_targets_creates_targets() -> None:
    g = make_game()
    g._spawn_targets(3)
    assert len(g.targets) == 3
    for t in g.targets:
        assert 0.3 <= t.depth <= 1.0
        assert 8 <= t.radius <= 20
        assert 50 <= t.score_base <= 300
        assert 0 <= t.color <= 3


def test_spawn_targets_deterministic_with_seed() -> None:
    g1 = make_game(42)
    g1._spawn_targets(5)
    g2 = make_game(42)
    g2._spawn_targets(5)
    for t1, t2 in zip(g1.targets, g2.targets):
        assert t1.x == t2.x
        assert t1.y == t2.y
        assert t1.depth == t2.depth
        assert t1.color == t2.color


# -- collision -----------------------------------------------------------

def test_check_target_hit_true() -> None:
    g = make_game()
    target = Target(x=100, y=100, depth=0.8, color=0, radius=12, score_base=200)
    arrow = Arrow(x=105, y=103, vx=0, vy=0, color=0)
    assert g._check_target_hit(arrow, target) is True


def test_check_target_hit_false() -> None:
    g = make_game()
    target = Target(x=100, y=100, depth=0.8, color=0, radius=12, score_base=200)
    arrow = Arrow(x=200, y=200, vx=0, vy=0, color=0)
    assert g._check_target_hit(arrow, target) is False


# -- combo / scoring -----------------------------------------------------

def test_combo_builds_on_same_color() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.arrow_color = 0  # RED
    target = Target(x=100, y=100, depth=1.0, color=0, radius=20, score_base=300)
    g._handle_hit(target)
    assert g.combo == 1
    assert g.heat == 0
    assert g.score > 0


def test_combo_resets_on_wrong_color() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.max_combo = 3
    g.arrow_color = 0  # RED
    target = Target(x=100, y=100, depth=1.0, color=1, radius=20, score_base=300)  # GREEN
    g._handle_hit(target)
    assert g.combo == 0
    assert g.heat == 1
    # arrow_color changes to target's color
    assert g.arrow_color == 1


def test_heat_builds_on_miss() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 2
    g._handle_miss()
    assert g.heat == 1
    assert g.combo == 0


def test_super_activates_at_combo_4() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.arrow_color = 0
    g.combo = 3  # one more hit triggers super
    target = Target(x=100, y=100, depth=1.0, color=0, radius=20, score_base=300)
    g._handle_hit(target)
    assert g.combo == 4
    assert g._is_super()
    assert g.super_timer == 5 * 30


def test_super_all_colors_match() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 100
    g.arrow_color = 0  # RED
    g.combo = 4
    target = Target(x=100, y=100, depth=1.0, color=1, radius=20, score_base=300)  # GREEN
    g._handle_hit(target)
    # in super, all colors match -> combo continues
    assert g.combo == 5
    assert g.heat == 0


def test_super_triple_score() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 100
    g.arrow_color = 0
    g.combo = 4
    target = Target(x=100, y=100, depth=1.0, color=0, radius=20, score_base=300)
    score_before = g.score
    g._handle_hit(target)
    gained = g.score - score_before
    expected = (300 + 5 * 50) * 3  # base + combo_bonus * 3
    assert gained == expected, f"expected {expected}, got {gained}"


def test_game_over_on_max_heat() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT - 1
    g._handle_miss()
    assert g.phase == Phase.GAME_OVER


def test_game_over_on_max_heat_from_wrong_hit() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT - 1
    g.arrow_color = 0
    target = Target(x=100, y=100, depth=1.0, color=1, radius=20, score_base=300)
    g._handle_hit(target)
    assert g.phase == Phase.GAME_OVER


# -- arrow physics -------------------------------------------------------

def test_arrow_gravity_applied() -> None:
    g = make_game()
    g._shoot_arrow(2.0, -3.0)
    assert g.arrow is not None
    initial_vy = g.arrow.vy
    g._update_arrow()
    assert g.arrow.vy == initial_vy + GRAVITY


def test_arrow_trail_grows() -> None:
    g = make_game()
    g._shoot_arrow(2.0, -3.0)
    assert g.arrow is not None
    assert len(g.arrow.trail) == 0
    g._update_arrow()
    assert len(g.arrow.trail) == 1


def test_arrow_off_screen_triggers_miss() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 0
    g._shoot_arrow(10.0, 0.0)  # flies right off screen fast
    for _ in range(50):
        if g.arrow is None or not g.arrow.alive:
            break
        g._update_arrow()
    assert g.arrow is not None
    assert not g.arrow.alive
    assert g.heat >= 1


# -- arrow color change --------------------------------------------------

def test_arrow_color_changes_on_same_color_hit() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.arrow_color = 2  # BLUE
    target = Target(x=100, y=100, depth=1.0, color=2, radius=20, score_base=300)
    g._handle_hit(target)
    assert g.arrow_color == 2  # same color, stays


def test_arrow_color_changes_on_wrong_color_hit() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.arrow_color = 0  # RED
    target = Target(x=100, y=100, depth=1.0, color=3, radius=20, score_base=300)  # YELLOW
    g._handle_hit(target)
    assert g.arrow_color == 3  # changes to target's color


# -- particles -----------------------------------------------------------

def test_hit_spawns_particles() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.arrow_color = 0
    target = Target(x=100, y=100, depth=1.0, color=0, radius=20, score_base=300)
    g._handle_hit(target)
    assert len(g.particles) > 0


def test_particles_fade_over_time() -> None:
    g = make_game()
    p = Particle(x=0, y=0, vx=0, vy=0, color=8, life=5, max_life=5)
    g.particles.append(p)
    initial_count = len(g.particles)
    for _ in range(10):
        g._update_particles()
    assert len(g.particles) < initial_count


# -- floating texts ------------------------------------------------------

def test_floating_texts_move_up_and_fade() -> None:
    g = make_game()
    ft = FloatingText(x=100, y=100, text="+100", color=7, life=30)
    g.floating_texts.append(ft)
    for _ in range(40):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0  # expired


# -- target drift --------------------------------------------------------

def test_target_bounces_off_edges() -> None:
    g = make_game(99)
    t = Target(x=5, y=100, depth=0.8, color=0, radius=10, score_base=200, vx=-0.5, vy=0)
    g.targets.append(t)
    g._update_targets()
    # should have bounced (vx positive now)
    assert t.vx > 0


# -- constants sanity ----------------------------------------------------

def test_constants() -> None:
    assert len(COLORS) == 4
    assert MAX_HEAT == 5
    assert SUPER_COMBO == 4
    assert MAX_TARGETS == 5
    assert MIN_ALIVE_TARGETS == 3
    assert GRAVITY == 0.15


# -- dataclass defaults --------------------------------------------------

def test_target_defaults() -> None:
    t = Target(x=0, y=0, depth=0.5, color=0, radius=10, score_base=100)
    assert t.alive is True
    assert t.vx == 0.0
    assert t.vy == 0.0


def test_arrow_defaults() -> None:
    a = Arrow(x=0, y=0, vx=1, vy=1, color=0)
    assert a.alive is True
    assert a.trail == []


def test_floating_text_defaults() -> None:
    ft = FloatingText(x=0, y=0, text="X", color=7, life=10)
    assert ft.life == 10


# -- is_super helper -----------------------------------------------------

def test_is_super_false_initially() -> None:
    g = make_game()
    assert not g._is_super()


def test_is_super_true_after_activate() -> None:
    g = make_game()
    g.super_timer = 100
    assert g._is_super()


# -- shoot arrow creates arrow with correct color ------------------------

def test_shoot_arrow_uses_current_arrow_color() -> None:
    g = make_game()
    g.arrow_color = 3  # YELLOW
    g._shoot_arrow(1.0, -2.0)
    assert g.arrow is not None
    assert g.arrow.color == 3


# -- max combo tracking --------------------------------------------------

def test_max_combo_tracks_peak() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.arrow_color = 0
    for i in range(3):
        t = Target(x=50 + i * 20, y=100, depth=1.0, color=0, radius=20, score_base=300)
        g._handle_hit(t)
    assert g.max_combo == 3

    # wrong color resets combo but max_combo stays
    g.arrow_color = 0
    t_bad = Target(x=200, y=100, depth=1.0, color=1, radius=20, score_base=300)
    g._handle_hit(t_bad)
    assert g.combo == 0
    assert g.max_combo == 3


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
