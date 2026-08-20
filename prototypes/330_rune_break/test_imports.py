"""Headless logic tests for RUNE BREAK (prototype 330_rune_break).

Run standalone:  uv run python prototypes/330_rune_break/test_imports.py
Run via pytest:  uv run pytest prototypes/330_rune_break/test_imports.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    CODE_LEN,
    MAX_GUESSES,
    PALETTE,
    START_LIVES,
    FloatText,
    Game,
    GuessRow,
    Particle,
    Phase,
    compute_feedback,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


# --- pure feedback ------------------------------------------------------

def test_feedback_all_exact():
    code = [8, 11, 5, 10]
    assert compute_feedback(code, code) == (4, 0)


def test_feedback_all_misplaced():
    assert compute_feedback([8, 11, 5, 10], [10, 5, 11, 8]) == (0, 4)


def test_feedback_mixed():
    assert compute_feedback([8, 11, 5, 10], [8, 11, 10, 5]) == (2, 2)


def test_feedback_none():
    assert compute_feedback([8, 11, 5, 10], [2, 12, 3, 1]) == (0, 0)


def test_feedback_duplicate_guess_no_double_count():
    # guess has 8 twice but code has 8 once -> the extra 8 must NOT count as misplaced
    assert compute_feedback([8, 8, 5, 10], [8, 11, 5, 10]) == (3, 0)


def test_feedback_empty_slots_ignored():
    assert compute_feedback([-1, -1, -1, -1], [8, 11, 5, 10]) == (0, 0)


# --- reset / initial state ---------------------------------------------

def test_reset_initial_state():
    g = make_game()
    assert g.phase is Phase.TITLE
    assert g.score == 0
    assert g.lives == START_LIVES
    assert g.codes_broken == 0
    assert g.streak == 0
    assert g.max_streak == 0
    assert g.guesses_used == 0
    assert g.current_guess == [-1] * CODE_LEN
    assert g.history == []
    assert g.revealed == set()
    assert g.cursor == 0


def test_code_valid_and_distinct():
    g = make_game()
    assert len(g.code) == CODE_LEN
    assert len(set(g.code)) == CODE_LEN  # no repeats
    assert all(c in PALETTE[:4] for c in g.code)  # codes_broken=0 -> 4 colors


def test_new_code_resets_turn_state():
    g = make_game()
    g.current_guess = [8, 11, 5, 10]
    g.history = [GuessRow([8, 11, 5, 10], 0, 4)]
    g.revealed = {0, 1}
    g.guesses_used = 5
    g._new_code()
    assert g.guesses_used == 0
    assert g.current_guess == [-1] * CODE_LEN
    assert g.history == []
    assert g.revealed == set()


def test_num_colors_escalation():
    g = make_game()
    g.codes_broken = 0
    assert g._num_colors() == 4
    g.codes_broken = 1
    assert g._num_colors() == 5
    g.codes_broken = 2
    assert g._num_colors() == 6
    g.codes_broken = 99
    assert g._num_colors() == 6


def test_code_uses_escalated_palette():
    g = make_game()
    g.codes_broken = 2
    g._new_code()
    assert all(c in PALETTE[:6] for c in g.code)


# --- slot editing -------------------------------------------------------

def test_place_color():
    g = make_game()
    g._place_color(2, 8)
    assert g.current_guess[2] == 8


def test_place_color_ignored_on_revealed_slot():
    g = make_game()
    g.revealed = {0}
    g.current_guess[0] = g.code[0]
    g._place_color(0, 10)
    assert g.current_guess[0] == g.code[0]  # unchanged


def test_clear_slot():
    g = make_game()
    g._place_color(1, 11)
    g._clear_slot(1)
    assert g.current_guess[1] == -1


def test_clear_slot_ignored_on_revealed_slot():
    g = make_game()
    g.revealed = {3}
    g.current_guess[3] = g.code[3]
    g._clear_slot(3)
    assert g.current_guess[3] == g.code[3]


def test_select_slot_clamps():
    g = make_game()
    g._select_slot(-5)
    assert g.cursor == 0
    g._select_slot(999)
    assert g.cursor == CODE_LEN - 1
    g._select_slot(2)
    assert g.cursor == 2


# --- submit guess -------------------------------------------------------

def test_submit_incomplete_rejected():
    g = make_game()
    g.current_guess = [8, 11, -1, 10]
    assert g._submit_guess() is False
    assert g.history == []
    assert g.guesses_used == 0


def test_submit_wrong_guess_records_history():
    g = make_game()
    g.phase = Phase.PLAYING
    wrong = [c for c in g.code]
    wrong[0] = PALETTE[(PALETTE.index(wrong[0]) + 1) % 4]  # a wrong color at pos 0
    g.current_guess = wrong
    assert g._submit_guess() is False
    assert len(g.history) == 1
    assert g.history[0].exact == 3  # 3 positions correct, 1 wrong
    assert g.guesses_used == 1
    assert g.phase is Phase.PLAYING


def test_submit_correct_solves():
    g = make_game()
    g.current_guess = list(g.code)
    assert g._submit_guess() is True
    assert g.phase is Phase.SOLVED
    assert g.codes_broken == 1
    assert g.streak == 1
    assert g.guesses_used == 1


def test_solve_bonus_first_guess():
    g = make_game()
    g.current_guess = list(g.code)
    g._submit_guess()
    # bonus = (8 - 1 + 1) * 150 + streak(1) * 100 = 1200 + 100 = 1300
    assert g.score == 1300


def test_solve_bonus_eighth_guess():
    g = make_game()
    g.guesses_used = 7
    g.current_guess = list(g.code)
    g._submit_guess()
    # bonus = (8 - 8 + 1) * 150 + 1 * 100 = 150 + 100 = 250
    assert g.score == 250


def test_streak_bonus_accumulates():
    g = make_game()
    # first solve
    g.current_guess = list(g.code)
    g._submit_guess()
    assert g.streak == 1 and g.max_streak == 1
    # advance to next code
    g.phase = Phase.PLAYING
    g._new_code()
    assert g.streak == 1  # streak preserved across codes
    # second solve
    g.current_guess = list(g.code)
    g._submit_guess()
    assert g.streak == 2
    assert g.max_streak == 2
    # score = 1300 + (1200 + 200) = 2700
    assert g.score == 2700


def test_solve_on_last_guess_wins_over_fail():
    g = make_game()
    g.guesses_used = MAX_GUESSES - 1  # 7 used, this is the 8th
    g.current_guess = list(g.code)
    g._submit_guess()
    assert g.phase is Phase.SOLVED  # solve wins, not fail
    assert g.lives == START_LIVES  # no life lost


# --- fail ---------------------------------------------------------------

def test_fail_loses_life_and_new_code():
    g = make_game()
    g.phase = Phase.PLAYING
    g.streak = 3
    g.lives = 3
    g._on_fail()
    assert g.lives == 2
    assert g.streak == 0
    assert g.phase is Phase.PLAYING
    assert g.guesses_used == 0  # new code reset the turn


def test_fail_on_last_life_game_over():
    g = make_game()
    g.lives = 1
    g.score = 500
    g.best_score = 0
    g._on_fail()
    assert g.lives == 0
    assert g.phase is Phase.GAME_OVER
    assert g.best_score == 500


def test_fail_does_not_improve_best_score():
    g = make_game()
    g.lives = 1
    g.score = 200
    g.best_score = 500
    g._on_fail()
    assert g.best_score == 500  # unchanged


# --- hint ---------------------------------------------------------------

def test_hint_reveals_code_and_costs_guess():
    g = make_game()
    g.cursor = 0
    assert g._hint_reveal() is True
    assert g.revealed == {0}
    assert g.current_guess[0] == g.code[0]
    assert g.guesses_used == 1


def test_hint_rejects_already_revealed():
    g = make_game()
    g.cursor = 0
    g._hint_reveal()
    assert g._hint_reveal() is False
    assert g.guesses_used == 1  # no second spend


def test_hint_rejects_when_no_guesses_left():
    g = make_game()
    g.guesses_used = MAX_GUESSES
    g.cursor = 0
    assert g._hint_reveal() is False
    assert g.revealed == set()


def test_hint_on_last_guess_does_not_fail():
    g = make_game()
    g.phase = Phase.PLAYING
    g.guesses_used = MAX_GUESSES - 1
    g.cursor = 1
    assert g._hint_reveal() is True
    assert g.phase is Phase.PLAYING  # hint is info, not a fail


# --- dataclasses --------------------------------------------------------

def test_dataclass_construction():
    row = GuessRow([8, 11, 5, 10], 2, 1)
    assert row.exact == 2 and row.misplaced == 1
    p = Particle(1.5, 2.5, 0.5, -0.5, 20, 8)
    assert p.x == 1.5 and p.color == 8
    ft = FloatText(10.0, 20.0, "CRACKED!", 50, 7)
    assert ft.text == "CRACKED!" and ft.life == 50


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
