"""test_imports.py — Headless logic tests for ECHO MEMORY."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/060_echo_memory")

from main import (
    Game, Phase, Panel, Particle, FloatingText,
    PANEL_LAYOUT, MAX_LIVES, ECHO_COMBO_THRESHOLD, ECHO_AUTO_COUNT, PANEL_COLORS,
)


def _make_game() -> Game:
    """Create a headless Game instance via __new__ bypass."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.font = None
    g.particles = []
    g.floats = []
    g._sx = 0
    g._sy = 0
    g._correct_color = 0
    g._correct_flash_timer = 0
    g.reset()
    return g


def test_panel_hit_test() -> None:
    """Panel.hit_test works."""
    p = Panel(50, 68, 105, 62, 8)
    assert p.hit_test(50, 68) is True
    assert p.hit_test(154, 68 + 62 - 1) is True
    assert p.hit_test(49, 68) is False


def test_game_new_bypass() -> None:
    """Game.__new__(Game) bypass works."""
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.lives == MAX_LIVES
    assert g.round_num == 1
    assert g.prev_color is None
    assert len(g.panels) == 4
    # Sequence is generated in reset()
    assert len(g._sequence) == g.round_num + 2


def test_generate_sequence_length() -> None:
    """Sequence length matches round_num + 2."""
    g = _make_game()
    assert len(g._sequence) == g.round_num + 2  # round 1: 3 items
    assert all(c in PANEL_COLORS for c in g._sequence)

    g.round_num = 5
    g._generate_sequence()
    assert len(g._sequence) == 7


def test_find_panel_at() -> None:
    """_find_panel_at finds correct panel or None."""
    g = _make_game()
    tl = g.panels[0]
    found = g._find_panel_at(tl.x + 10, tl.y + 10)
    assert found is not None
    assert found.color == tl.color  # RED = 8
    assert g._find_panel_at(0, 0) is None


def test_check_click() -> None:
    """_check_click validates against sequence position."""
    g = _make_game()
    g._sequence = [8, 3, 5]
    g._player_idx = 0
    assert g._check_click(8) is True
    assert g._check_click(3) is False
    g._player_idx = 3  # past end
    assert g._check_click(5) is False


def test_process_correct_new_color() -> None:
    """_process_correct: first press (no previous color match)."""
    g = _make_game()
    g._sequence = [8, 3, 5]
    g._player_idx = 0
    g.prev_color = None
    g.combo = 0

    bonus, done, echo = g._process_correct(8)
    assert bonus == 10  # 10 + 0*5
    assert done is False
    assert echo is False
    assert g._player_idx == 1
    assert g.prev_color == 8
    assert g.combo == 0  # no match, stays 0


def test_process_correct_same_color() -> None:
    """_process_correct: consecutive same color builds combo."""
    g = _make_game()
    g._sequence = [8, 8, 3]
    g._player_idx = 0
    g.prev_color = 8  # simulate first press already done
    g.combo = 0

    # Press RED (matches prev_color=8)
    bonus, done, echo = g._process_correct(8)
    assert bonus == 10  # combo was 0 before match
    assert g.combo == 1
    assert g.max_combo == 1
    assert g._player_idx == 1


def test_process_correct_different_color() -> None:
    """_process_correct: different color resets combo."""
    g = _make_game()
    g._sequence = [8, 3, 5]
    g._player_idx = 1  # expecting GREEN (3) at position 1
    g.prev_color = 8  # simulate previous press was RED
    g.combo = 2  # had a combo going

    bonus, done, echo = g._process_correct(3)  # GREEN != RED
    assert g.combo == 0  # reset
    assert bonus == 20  # 10 + 2*5
    assert g.prev_color == 3


def test_process_correct_round_complete() -> None:
    """_process_correct: done=True when last position and no echo."""
    g = _make_game()
    g._sequence = [8, 3]
    g._player_idx = 1  # one more to go
    g.prev_color = 8
    g.combo = 0

    bonus, done, echo = g._process_correct(3)
    assert done is True
    assert echo is False
    assert g._player_idx == 2


def test_process_wrong() -> None:
    """_process_wrong decrements lives and resets combo."""
    g = _make_game()
    g.lives = 3
    g.combo = 5
    g.prev_color = 8
    remaining = g._process_wrong(3)
    assert remaining == 2
    assert g.lives == 2
    assert g.combo == 0
    assert g.prev_color is None


def test_echo_chain_trigger() -> None:
    """Combo >= ECHO_COMBO_THRESHOLD (3) triggers echo."""
    g = _make_game()
    # Need combo to reach 3 → 4 same-color presses after initial
    g._sequence = [8, 8, 8, 8, 3, 5]
    g._player_idx = 3  # 3 presses already done (all RED)
    g.prev_color = 8
    g.combo = 2  # after 3 same-color presses (index 0→combo=0, 1→combo=1, 2→combo=2)

    bonus, done, echo = g._process_correct(8)
    assert g.combo == 3  # matched again
    assert echo is True  # combo >= 3 AND _player_idx (4) < len(6)
    assert done is False


def test_echo_chain_no_trigger_on_last() -> None:
    """Echo does NOT trigger when no positions remain."""
    g = _make_game()
    g._sequence = [8, 8, 8, 8]
    g._player_idx = 3
    g.prev_color = 8
    g.combo = 2

    bonus, done, echo = g._process_correct(8)
    assert g.combo == 3
    assert echo is False  # _player_idx (4) >= len(4)
    assert done is True  # sequence complete


def test_game_over_on_zero_lives() -> None:
    """Lives reaching 0 returns 0."""
    g = _make_game()
    g.lives = 1
    remaining = g._process_wrong(8)
    assert remaining == 0


def test_calc_echo_score() -> None:
    """_calc_echo_score: bonus = 10 + combo * 10."""
    g = _make_game()
    g.combo = 3
    assert g._calc_echo_score(8) == 40  # 10 + 3*10
    g.combo = 5
    assert g._calc_echo_score(3) == 60


def test_max_combo_tracking() -> None:
    """max_combo tracks the highest combo seen."""
    g = _make_game()
    g._sequence = [8, 8, 3, 3, 5]
    g._player_idx = 0
    g.prev_color = None
    g.combo = 0

    g._process_correct(8)  # combo=0
    g._process_correct(8)  # combo=1
    assert g.max_combo == 1
    g._process_correct(3)  # combo=0 (reset)
    g._process_correct(3)  # combo=1
    assert g.max_combo == 1  # still max=1


def test_round_complete() -> None:
    """_round_complete adds round bonus and advances round."""
    g = _make_game()
    g.round_num = 3
    g.score = 100
    g._round_complete()
    assert g.score == 100 + 3 * 50  # 250
    assert g.round_num == 4


def test_speed_property() -> None:
    """_speed property returns correct values."""
    g = _make_game()
    g.round_num = 1
    assert g._speed == 1.0
    g.round_num = 3
    assert g._speed == 1.0
    g.round_num = 4
    assert g._speed == 1.3
    g.round_num = 7
    assert g._speed == 1.6
    g.round_num = 10
    assert g._speed == 2.0


def test_start_echo_chain() -> None:
    """_start_echo_chain computes remaining echo count."""
    g = _make_game()
    g._sequence = [8] * 8
    g._player_idx = 4  # 4 remaining positions
    remaining = g._start_echo_chain()
    assert remaining == min(ECHO_AUTO_COUNT, 4)  # 2
    assert g._echo_left == 2

    # Only 1 position left
    g._player_idx = 7
    remaining = g._start_echo_chain()
    assert remaining == 1
    assert g._echo_left == 1


def test_reset_clears_state() -> None:
    """reset() brings everything back to initial."""
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 5
    g.lives = 0
    g.round_num = 10
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.lives == MAX_LIVES
    assert g.round_num == 1
    assert len(g._sequence) == g.round_num + 2
    assert g._player_idx == 0


def test_panel_layout_colors() -> None:
    """PANEL_LAYOUT has exactly RED, GREEN, DARK_BLUE, YELLOW."""
    colors = [p[2] for p in PANEL_LAYOUT]
    assert set(colors) == {8, 3, 5, 10}


def test_phase_enum() -> None:
    """All phases present."""
    assert Phase.TITLE == 0
    assert Phase.SHOW_SEQUENCE == 1
    assert Phase.PLAYER_TURN == 2
    assert Phase.ECHO_CHAIN == 3
    assert Phase.MISS_ANIM == 4
    assert Phase.GAME_OVER == 5


def test_particle_dataclass() -> None:
    """Particle fields correct."""
    p = Particle(100.0, 50.0, 2.0, -1.0, 20, 8)
    assert p.x == 100.0
    assert p.life == 20


def test_floating_text_dataclass() -> None:
    """FloatingText fields correct."""
    ft = FloatingText(10.0, 20.0, "COMBO!", 30, 7)
    assert ft.text == "COMBO!"
    assert ft.life == 30


def test_correct_click_wrong_color_check_first() -> None:
    """_process_correct returns 0,False,False when _check_click fails."""
    g = _make_game()
    g._sequence = [8]
    g._player_idx = 0
    bonus, done, echo = g._process_correct(3)  # wrong color
    assert bonus == 0
    assert done is False
    assert echo is False
    assert g._player_idx == 0  # not advanced


if __name__ == "__main__":
    test_panel_hit_test()
    test_game_new_bypass()
    test_generate_sequence_length()
    test_find_panel_at()
    test_check_click()
    test_process_correct_new_color()
    test_process_correct_same_color()
    test_process_correct_different_color()
    test_process_correct_round_complete()
    test_process_wrong()
    test_echo_chain_trigger()
    test_echo_chain_no_trigger_on_last()
    test_game_over_on_zero_lives()
    test_calc_echo_score()
    test_max_combo_tracking()
    test_round_complete()
    test_speed_property()
    test_start_echo_chain()
    test_reset_clears_state()
    test_panel_layout_colors()
    test_phase_enum()
    test_particle_dataclass()
    test_floating_text_dataclass()
    test_correct_click_wrong_color_check_first()
    print("OK: All 24 headless tests passed!")
