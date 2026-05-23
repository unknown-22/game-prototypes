from __future__ import annotations

import sys
import types

_mock_pyxel = types.ModuleType("pyxel")
for _name, _value in {
    "COLOR_BLACK": 0,
    "COLOR_NAVY": 1,
    "COLOR_PURPLE": 2,
    "COLOR_GREEN": 3,
    "COLOR_BROWN": 4,
    "COLOR_DARK_BLUE": 5,
    "COLOR_LIGHT_BLUE": 6,
    "COLOR_WHITE": 7,
    "COLOR_RED": 8,
    "COLOR_ORANGE": 9,
    "COLOR_YELLOW": 10,
    "COLOR_LIME": 11,
    "COLOR_CYAN": 12,
    "COLOR_GRAY": 13,
    "COLOR_PINK": 14,
    "COLOR_PEACH": 15,
    "KEY_RETURN": 16,
    "KEY_SPACE": 17,
    "KEY_R": 18,
    "KEY_RIGHT": 19,
    "KEY_D": 20,
    "KEY_LEFT": 21,
    "KEY_A": 22,
    "KEY_DOWN": 23,
    "KEY_S": 24,
    "KEY_UP": 25,
    "KEY_W": 26,
}.items():
    setattr(_mock_pyxel, _name, _value)
setattr(_mock_pyxel, "btn", lambda _key: False)
setattr(_mock_pyxel, "btnp", lambda _key: False)
sys.modules["pyxel"] = _mock_pyxel

from main import (  # noqa: E402
    CHARGE_MAX,
    CONVERGE_DAMAGE,
    GAME_SECONDS,
    OVERLOAD_COST,
    SCREEN_H,
    SCREEN_W,
    Enemy,
    GameState,
    Phase,
    clamp,
    distance,
)


def test_constants_are_project_shape() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert GAME_SECONDS == 90
    assert OVERLOAD_COST < CHARGE_MAX
    assert CONVERGE_DAMAGE > 0


def test_clamp_and_distance() -> None:
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
    assert distance(0, 0, 3, 4) == 5


def test_state_starts_at_title() -> None:
    state = GameState(seed=1)
    assert state.phase == Phase.TITLE
    state.start()
    assert state.phase == Phase.PLAYING
    assert state.player.hp > 0


def test_overload_requires_charge_and_targets() -> None:
    state = GameState(seed=1)
    state.start()
    state.player.charge = OVERLOAD_COST
    state.enemies = [
        Enemy(130, 100, 20, 0.0),
        Enemy(145, 106, 20, 0.0),
        Enemy(160, 95, 20, 0.0),
    ]
    assert state.can_overload()
    assert state.trigger_overload()
    assert len(state.split_paths) == 3
    assert len(state.convergences) == 1
    assert state.player.charge < OVERLOAD_COST


def test_convergence_rewards_tight_clusters() -> None:
    tight = GameState(seed=1)
    tight.start()
    tight.enemies = [Enemy(150, 110, 20, 0.0), Enemy(156, 112, 20, 0.0), Enemy(162, 109, 20, 0.0)]
    loose = GameState(seed=1)
    loose.start()
    loose.enemies = [Enemy(80, 70, 20, 0.0), Enemy(180, 130, 20, 0.0), Enemy(250, 190, 20, 0.0)]
    tight_plan = tight.plan_overload()
    loose_plan = loose.plan_overload()
    assert tight_plan is not None
    assert loose_plan is not None
    assert tight_plan.damage > loose_plan.damage
    assert tight_plan.radius > loose_plan.radius
