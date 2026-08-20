"""Headless logic tests for EYEBALL (prototype 329_eyeball).

Run standalone:  uv run python prototypes/329_eyeball/test_imports.py
Run via pytest:  uv run pytest prototypes/329_eyeball/test_imports.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    GAME_DURATION,
    MAX_COUNT,
    Confidence,
    Game,
    Phase,
    TaskState,
    TaskType,
    _count_range,
    _flash_frames,
    _score_guess,
    _solve_window,
    _tolerance_for,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


# --- pure scoring -------------------------------------------------------

def test_score_perfect_safe():
    pts, label = _score_guess(10, 10, Confidence.SAFE, 0)
    assert pts == 20 + 10 + 30
    assert label == "PERFECT!"


def test_score_perfect_risky():
    pts, label = _score_guess(10, 10, Confidence.RISKY, 0)
    assert pts == 20 * 3 + 10 + 30
    assert label == "PERFECT!"


def test_score_hit_safe_within_tolerance():
    pts, label = _score_guess(10, 14, Confidence.SAFE, 0)
    assert pts == 20 + 10
    assert label == "HIT!"


def test_score_hit_risky_within_tolerance():
    pts, label = _score_guess(10, 11, Confidence.RISKY, 0)
    assert pts == 20 * 3 + 10
    assert label == "HIT!"


def test_score_miss_safe_out_of_tolerance():
    pts, label = _score_guess(10, 15, Confidence.SAFE, 0)
    assert pts == 0
    assert label == "MISS"


def test_score_miss_risky_out_of_tolerance():
    pts, label = _score_guess(10, 12, Confidence.RISKY, 0)
    assert pts == 0
    assert label == "MISS"


def test_score_streak_bonus():
    pts, label = _score_guess(10, 10, Confidence.SAFE, 3)
    assert pts == 20 + (3 + 1) * 10 + 30
    assert label == "PERFECT!"


def test_tolerance_values():
    assert _tolerance_for(Confidence.SAFE) == 4
    assert _tolerance_for(Confidence.RISKY) == 1


def test_risk_reward_gradient():
    # A risky guess off by 2 loses everything; the same guess as SAFE hits.
    risky_pts, _ = _score_guess(10, 12, Confidence.RISKY, 0)
    safe_pts, _ = _score_guess(10, 12, Confidence.SAFE, 0)
    assert risky_pts == 0
    assert safe_pts > 0
    # A dead-on risky guess outscores a dead-on safe guess.
    risky_perfect, _ = _score_guess(10, 10, Confidence.RISKY, 0)
    safe_perfect, _ = _score_guess(10, 10, Confidence.SAFE, 0)
    assert risky_perfect > safe_perfect


# --- escalation helpers -------------------------------------------------

def test_flash_frames_escalation():
    assert _flash_frames(0) == 40
    assert _flash_frames(3600) == 12
    assert _flash_frames(0) >= _flash_frames(1800) >= _flash_frames(3600)


def test_count_range_escalation():
    assert _count_range(0) == (5, 16)
    assert _count_range(3600) == (5, 34)
    lo, hi = _count_range(3600)
    assert lo == 5 and hi <= MAX_COUNT


def test_solve_window_escalation():
    assert _solve_window(0) == 260
    assert _solve_window(3600) == 140
    assert _solve_window(0) >= _solve_window(3600)


# --- task lifecycle -----------------------------------------------------

def test_new_task_alternates_and_ranges():
    g = make_game(42)
    g.tasks_done = 0
    g.frame = 0
    g._new_task()
    assert g.task_type is TaskType.COUNT
    lo, hi = _count_range(0)
    assert lo <= g.truth <= hi
    assert len(g.dots) == g.truth
    g.tasks_done = 1
    g._new_task()
    assert g.task_type is TaskType.FRACTION
    assert 10 <= g.truth <= 90
    assert g.dots == []


def test_new_task_uses_seeded_rng_deterministic():
    a = make_game(42)
    b = make_game(42)
    a._new_task()
    b._new_task()
    assert a.truth == b.truth
    assert a.task_type is b.task_type


def test_resolve_hit_updates_state():
    g = make_game(42)
    g.phase = Phase.PLAYING
    g.task_state = TaskState.GUESS
    g.truth = 12
    g.estimate = 12
    g.confidence = Confidence.RISKY
    g._resolve_guess()
    assert g.score == 100
    assert g.streak == 1
    assert g.tasks_done == 1
    assert g.task_state is TaskState.REVEAL
    assert g.best_score == 100
    assert g.result_label == "PERFECT!"


def test_resolve_miss_resets_streak():
    g = make_game(42)
    g.phase = Phase.PLAYING
    g.streak = 5
    g.truth = 50
    g.estimate = 5
    g.confidence = Confidence.SAFE
    g._resolve_guess()
    assert g.score == 0
    assert g.streak == 0
    assert g.tasks_done == 1
    assert g.result_label == "MISS"


def test_resolve_streak_accumulates():
    g = make_game(42)
    g.phase = Phase.PLAYING
    g.task_state = TaskState.GUESS
    for i in range(3):
        g.truth = 20
        g.estimate = 20
        g.confidence = Confidence.SAFE
        g.task_state = TaskState.GUESS
        g._resolve_guess()
    # streak 0->1->2->3; 3rd resolve used streak=2 -> points 20 + 3*10 + 30 = 80
    assert g.streak == 3
    assert g.score == (20 + 10 + 30) + (20 + 20 + 30) + (20 + 30 + 30)


def test_advance_time_up():
    g = make_game(42)
    g.frame = GAME_DURATION
    g._advance()
    assert g.phase is Phase.GAME_OVER


def test_advance_continues():
    g = make_game(42)
    g.frame = GAME_DURATION - 1
    g._advance()
    assert g.phase is Phase.TITLE  # _new_task does not change phase
    assert g.task_state is TaskState.SHOW


def test_reset_initial_state():
    g = make_game(42)
    assert g.phase is Phase.TITLE
    assert g.frame == 0
    assert g.score == 0
    assert g.streak == 0
    assert g.tasks_done == 0
    assert g.confidence is Confidence.SAFE
    assert g.task_state is TaskState.SHOW
    assert g.particles == []
    assert g.floats == []
    assert g.dots == []


def test_reset_preserves_seeded_rng():
    g = Game.__new__(Game)
    g.rng = random.Random(7)
    g.best_score = 1234
    g.reset()
    assert g.rng is not None
    assert g.best_score == 1234


# --- runner -------------------------------------------------------------

def main() -> int:
    tests = [
        v
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
