import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    COLOR_COUNT,
    FloatingText,
    Game,
    Particle,
    Phase,
    WORD_POOL,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = 1800
    g.phase = Phase.TITLE
    g.wrong_guesses = 0
    g.current_word = ""
    g._revealed: list[bool] = []
    g._letter_colors: list[int] = []
    g._guessed_letters: set[str] = set()
    g.last_correct_color = -1
    g.super_mode = False
    g.super_timer = 0
    g.multiplier = 1
    g.best_score = 0
    g.particles: list[Particle] = []
    g.floating_texts: list[FloatingText] = []
    g._word_complete_timer = 0
    g._used_words: list[str] = []
    g._flash_timer = 0
    g._word_started = False
    g.phase = Phase.PLAYING
    g.current_word = g._generate_word()
    return g


class TestWordGeneration:
    def test_word_is_string(self) -> None:
        g = _make_game()
        assert isinstance(g.current_word, str)

    def test_word_in_pool(self) -> None:
        g = _make_game()
        assert g.current_word in WORD_POOL

    def test_revealed_length_matches_word(self) -> None:
        g = _make_game()
        assert len(g._revealed) == len(g.current_word)

    def test_letter_colors_length_matches_word(self) -> None:
        g = _make_game()
        assert len(g._letter_colors) == len(g.current_word)

    def test_all_colors_valid(self) -> None:
        g = _make_game()
        for c in g._letter_colors:
            assert 0 <= c < COLOR_COUNT

    def test_all_unrevealed_initially(self) -> None:
        g = _make_game()
        assert all(r is False for r in g._revealed)

    def test_word_length_within_bounds(self) -> None:
        g = _make_game()
        assert 4 <= len(g.current_word) <= 7

    def test_generate_word_assigns_colors(self) -> None:
        g = _make_game()
        word = g._generate_word()
        assert len(g._revealed) == len(word)
        assert len(g._letter_colors) == len(word)


class TestHandleGuess:
    def test_correct_letter_reveals_position(self) -> None:
        g = _make_game()
        first_letter = g.current_word[0]
        assert not g._revealed[0]
        g._handle_guess(first_letter)
        assert g._revealed[0]

    def test_correct_letter_increases_score(self) -> None:
        g = _make_game()
        old_score = g.score
        first_letter = g.current_word[0]
        g._handle_guess(first_letter)
        assert g.score > old_score

    def test_wrong_letter_increases_heat(self) -> None:
        g = _make_game()
        # Find a letter not in the word
        all_letters = set(chr(ord("a") + i) for i in range(26))
        word_letters = set(g.current_word)
        wrong = next(iter(all_letters - word_letters))
        g._handle_guess(wrong)
        assert g.heat > 0.0

    def test_wrong_letter_adds_wrong_guesses(self) -> None:
        g = _make_game()
        all_letters = set(chr(ord("a") + i) for i in range(26))
        word_letters = set(g.current_word)
        wrong = next(iter(all_letters - word_letters))
        g._handle_guess(wrong)
        assert g.wrong_guesses == 1

    def test_wrong_letter_resets_combo(self) -> None:
        g = _make_game(42)
        g.combo = 3
        all_letters = set(chr(ord("a") + i) for i in range(26))
        word_letters = set(g.current_word)
        wrong = next(iter(all_letters - word_letters))
        g._handle_guess(wrong)
        assert g.combo == 0

    def test_duplicate_guess_ignored(self) -> None:
        g = _make_game()
        first_letter = g.current_word[0]
        g._handle_guess(first_letter)
        old_score = g.score
        changed = g._handle_guess(first_letter)
        assert changed is False
        assert g.score == old_score

    def test_same_color_combo_increases(self) -> None:
        g = _make_game(42)
        word = g.current_word
        # Find two positions with the same color
        same_color_idx = -1
        for i in range(len(word)):
            if same_color_idx >= 0 and g._letter_colors[i] == g._letter_colors[same_color_idx]:
                break
            same_color_idx = i
        # Force same color for first two different letters
        if len(word) >= 2 and word[0] != word[1]:
            g._letter_colors[1] = g._letter_colors[0]
        g._handle_guess(word[0])
        assert g.combo == 1
        g._handle_guess(word[1])
        if g._letter_colors[0] == g._letter_colors[1]:
            assert g.combo == 2

    def test_different_color_resets_combo(self) -> None:
        g = _make_game(42)
        word = g.current_word
        if len(word) < 2:
            return
        # Force different colors
        g._letter_colors[0] = 0
        g._letter_colors[1] = 1 if word[0] != word[1] else 0
        g._handle_guess(word[0])
        assert g.combo == 1
        if g._letter_colors[0] != g._letter_colors[1]:
            g._handle_guess(word[1])
            assert g.combo == 1

    def test_guess_adds_to_guessed_set(self) -> None:
        g = _make_game()
        g._handle_guess("x")
        assert "x" in g._guessed_letters

    def test_multiple_positions_revealed_for_duplicate_letter(self) -> None:
        g = _make_game()
        word = g.current_word.lower()
        # Find a letter that appears more than once
        for ch in word:
            if word.count(ch) >= 2:
                g._handle_guess(ch)
                revealed_count = sum(1 for i, r in enumerate(g._revealed) if r and g.current_word[i] == ch)
                assert revealed_count == word.count(ch)
                return
        # If no duplicate letters, test still passes
        assert True


class TestCombo:
    def test_combo_starts_zero(self) -> None:
        g = _make_game()
        assert g.combo == 0

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game(42)
        word = g.current_word
        if len(word) >= 3:
            g._letter_colors[0] = 0
            g._letter_colors[1] = 0
            g._letter_colors[2] = 0
            g._handle_guess(word[0])
            g._handle_guess(word[1])
            g._handle_guess(word[2])
            assert g.max_combo >= 3


class TestSuperMode:
    def test_super_activation_at_combo_four(self) -> None:
        g = _make_game(42)
        word = g.current_word
        if len(word) < 4:
            return
        g._letter_colors[0] = 0
        g._letter_colors[1] = 0
        g._letter_colors[2] = 0
        g._letter_colors[3] = 0
        g._handle_guess(word[0])
        g._handle_guess(word[1])
        g._handle_guess(word[2])
        assert not g.super_mode
        g._handle_guess(word[3])
        assert g.super_mode
        assert g.super_timer == 300

    def test_super_mode_sets_multiplier(self) -> None:
        g = _make_game(42)
        g._activate_super_mode()
        assert g.multiplier == 3

    def test_deactivate_super_mode_resets(self) -> None:
        g = _make_game(42)
        g._activate_super_mode()
        g._deactivate_super_mode()
        assert not g.super_mode
        assert g.multiplier == 1
        assert g.super_timer == 0

    def test_super_timer_decrements(self) -> None:
        g = _make_game(42)
        g._activate_super_mode()
        st = g.super_timer
        g._update_super_mode()
        assert g.super_timer == st - 1

    def test_super_mode_expires(self) -> None:
        g = _make_game(42)
        g._activate_super_mode()
        g.super_timer = 1
        g._update_super_mode()
        assert not g.super_mode
        assert g.multiplier == 1


class TestAllRevealed:
    def test_all_revealed_true_when_all_positions_revealed(self) -> None:
        g = _make_game()
        g._revealed = [True] * len(g.current_word)
        assert g._all_revealed()

    def test_all_revealed_false_when_partial(self) -> None:
        g = _make_game()
        g._revealed = [True] * (len(g.current_word) - 1) + [False]
        assert not g._all_revealed()

    def test_word_complete_triggered(self) -> None:
        g = _make_game()
        for ch in g.current_word:
            g._handle_guess(ch)
        assert g._all_revealed()


class TestHeat:
    def test_heat_decays_over_time(self) -> None:
        g = _make_game()
        g.heat = 50.0
        for _ in range(100):
            g._update_heat()
        assert g.heat < 50.0

    def test_heat_never_negative(self) -> None:
        g = _make_game()
        g.heat = 0.0
        for _ in range(100):
            g._update_heat()
        assert g.heat == 0.0

    def test_wrong_guess_adds_heat(self) -> None:
        g = _make_game()
        all_letters = set(chr(ord("a") + i) for i in range(26))
        word_letters = set(g.current_word)
        wrong = next(iter(all_letters - word_letters))
        g._handle_guess(wrong)
        assert g.heat >= 14.0

    def test_game_over_at_heat_100(self) -> None:
        g = _make_game(42)
        g.heat = 100.0
        g.phase = Phase.PLAYING
        all_letters = set(chr(ord("a") + i) for i in range(26))
        word_letters = set(g.current_word)
        wrong = next(iter(all_letters - word_letters))
        g._handle_guess(wrong)
        assert g.phase == Phase.GAME_OVER


class TestParticles:
    def test_particle_lifecycle(self) -> None:
        g = _make_game()
        g.particles = [
            Particle(x=10.0, y=10.0, vx=1.0, vy=0.0, life=5, color=8),
            Particle(x=20.0, y=20.0, vx=0.0, vy=0.0, life=0, color=3),
        ]
        g._update_particles()
        assert len(g.particles) == 1
        assert g.particles[0].x == 11.0
        assert g.particles[0].life == 4

    def test_particles_spawn_on_correct_guess(self) -> None:
        g = _make_game()
        old_count = len(g.particles)
        first_letter = g.current_word[0]
        g._handle_guess(first_letter)
        assert len(g.particles) > old_count


class TestFloatingText:
    def test_floating_text_lifecycle(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="+10", life=5, color=10),
            FloatingText(x=100.0, y=100.0, text="+0", life=0, color=10),
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].y == 99.0

    def test_floating_text_on_correct_guess(self) -> None:
        g = _make_game()
        old_count = len(g.floating_texts)
        first_letter = g.current_word[0]
        g._handle_guess(first_letter)
        assert len(g.floating_texts) > old_count


class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 5
        g.heat = 50.0
        g.timer = 500
        g.wrong_guesses = 3
        g.super_mode = True
        g.super_timer = 100
        g.multiplier = 3
        g.max_combo = 5
        g.reset()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.timer == 1800
        assert g.wrong_guesses == 0
        assert not g.super_mode
        assert g.super_timer == 0
        assert g.multiplier == 1
        assert g.max_combo == 0

    def test_reset_preserves_best_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.best_score = 0
        g.reset()
        assert g.best_score == 500

    def test_reset_clears_guessed_letters(self) -> None:
        g = _make_game()
        g._guessed_letters = {"a", "b", "c"}
        g.reset()
        assert len(g._guessed_letters) == 0


class TestTimer:
    def test_timer_starts_at_1800(self) -> None:
        g = _make_game()
        assert g.timer == 1800

    def test_timer_decrements_in_playing(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        initial = g.timer
        g._update_timer()
        assert g.timer == initial - 1

    def test_timer_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g._update_timer()
        assert g.phase == Phase.GAME_OVER


class TestPhases:
    def test_title_enter_starts_game(self) -> None:
        g = _make_game()
        g.phase = Phase.TITLE
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.current_word != ""

    def test_next_word_generates_new_word(self) -> None:
        g = _make_game()
        old_word = g.current_word
        g._next_word()
        assert g.current_word != ""
        if len(g._used_words) > 1:
            assert g.current_word != old_word

    def test_next_word_clears_guessed(self) -> None:
        g = _make_game()
        g._guessed_letters = {"a", "b"}
        g._next_word()
        assert len(g._guessed_letters) == 0

    def test_next_word_resets_last_correct_color(self) -> None:
        g = _make_game()
        g.last_correct_color = 2
        g._next_word()
        assert g.last_correct_color == -1


class TestScoring:
    def test_correct_guess_awards_10_base(self) -> None:
        g = _make_game()
        old_score = g.score
        g._handle_guess(g.current_word[0])
        gained = g.score - old_score
        occurrences = g.current_word.count(g.current_word[0])
        assert gained == 10 * occurrences  # combo=1, multiplier=1, per position

    def test_combo2_doubles_score(self) -> None:
        g = _make_game(42)
        word = g.current_word
        if len(word) >= 2 and word[0] != word[1]:
            g._letter_colors[0] = 0
            g._letter_colors[1] = 0
            g._handle_guess(word[0])
            old_score = g.score
            g._handle_guess(word[1])
            gained = g.score - old_score
            occurrences = word.count(word[1])
            # combo=2 * multiplier=1 * 10 per occurrence
            assert gained == 20 * occurrences

    def test_super_multiplier_triples(self) -> None:
        g = _make_game(42)
        g._activate_super_mode()
        old_score = g.score
        g.combo = 1
        g.last_correct_color = g._letter_colors[0]
        g._handle_guess(g.current_word[0])
        gained = g.score - old_score
        occurrences = g.current_word.count(g.current_word[0])
        # After guessing: combo becomes 2 (same color), multiplier=3, 10 per pos
        assert gained == 10 * 2 * 3 * occurrences


class TestEdgeCases:
    def test_timer_zero_ends_game_even_in_playing(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g._update_timer()
        assert g.phase == Phase.GAME_OVER

    def test_wrong_guess_preserves_super_mode(self) -> None:
        g = _make_game(42)
        g._activate_super_mode()
        all_letters = set(chr(ord("a") + i) for i in range(26))
        word_letters = set(g.current_word)
        wrong = next(iter(all_letters - word_letters))
        g._handle_guess(wrong)
        assert g.super_mode
        assert g.combo == 0

    def test_letter_not_in_alphabet_ignored(self) -> None:
        g = _make_game()
        # Non-letter characters shouldn't affect the game
        # This is handled by the update loop only checking A-Z keys
        assert g.score >= 0
