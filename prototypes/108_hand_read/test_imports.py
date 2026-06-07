"""test_imports.py — Headless logic tests for Hand Read."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/108_hand_read")

from main import (  # noqa: E402
    BEAT_MAP,
    HAND_COLORS,
    LIME,
    CYAN,
    RED,
    Game,
    Particle,
    Phase,
    WHITE,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.queue = []
    g.ai_hp = Game.AI_MAX_HP
    g.player_hp = Game.PLAYER_MAX_HP
    g.energy = Game.MAX_ENERGY
    g.combo = 0
    g.same_hand_streak = 0
    g.last_hand = -1
    g.max_combo = 0
    g.score = 0
    g.ai_prediction = 0
    g.player_history = []
    g.ai_history = []
    g.phase_timer = 0
    g.super_mode = False
    g.super_timer = 0
    g.turn_count = 0
    g.result_text = ""
    g.result_color = WHITE
    g.current_player_hand = -1
    g.current_ai_hand = -1
    g.battle_frame = 0
    g.particles = []
    g._shake_frames = 0
    g._prev_mouse_pressed = False
    g.high_score = 0
    g.reset()
    return g


# ── Constants ──
def test_constants():
    assert HAND_COLORS[0] == RED  # ROCK
    assert HAND_COLORS[1] == LIME  # PAPER
    assert HAND_COLORS[2] == CYAN  # SCISSORS
    assert BEAT_MAP[0] == 2  # ROCK beats SCISSORS
    assert BEAT_MAP[1] == 0  # PAPER beats ROCK
    assert BEAT_MAP[2] == 1  # SCISSORS beats PAPER


# ── _resolve_battle ──
def test_resolve_battle_win():
    assert Game._resolve_battle(Game, 0, 2) == (0, 1, True, False)  # ROCK beats SCISSORS
    assert Game._resolve_battle(Game, 1, 0) == (0, 1, True, False)  # PAPER beats ROCK
    assert Game._resolve_battle(Game, 2, 1) == (0, 1, True, False)  # SCISSORS beats PAPER


def test_resolve_battle_lose():
    assert Game._resolve_battle(Game, 0, 1) == (1, 0, False, False)  # ROCK loses to PAPER
    assert Game._resolve_battle(Game, 1, 2) == (1, 0, False, False)  # PAPER loses to SCISSORS
    assert Game._resolve_battle(Game, 2, 0) == (1, 0, False, False)  # SCISSORS loses to ROCK


def test_resolve_battle_tie():
    assert Game._resolve_battle(Game, 0, 0) == (0, 0, False, True)
    assert Game._resolve_battle(Game, 1, 1) == (0, 0, False, True)
    assert Game._resolve_battle(Game, 2, 2) == (0, 0, False, True)


# ── _shrink_history_window ──
def test_shrink_history_window():
    assert Game._shrink_history_window(Game, 10) == 8
    assert Game._shrink_history_window(Game, 7) == 8
    assert Game._shrink_history_window(Game, 6) == 6
    assert Game._shrink_history_window(Game, 4) == 6
    assert Game._shrink_history_window(Game, 3) == 4
    assert Game._shrink_history_window(Game, 1) == 4


# ── _update_combo ──
def test_update_combo_first_win():
    g = _make_game()
    g._update_combo(True, 0)
    assert g.combo == 1
    assert g.last_hand == 0
    assert g.same_hand_streak == 1
    assert g.max_combo == 1


def test_update_combo_same_hand_streak():
    g = _make_game()
    g.last_hand = 0
    g.combo = 2
    g.same_hand_streak = 2
    g.max_combo = 2
    g._update_combo(True, 0)
    assert g.combo == 3
    assert g.same_hand_streak == 3


def test_update_combo_different_hand():
    g = _make_game()
    g.last_hand = 0
    g.combo = 2
    g._update_combo(True, 1)
    assert g.combo == 1
    assert g.last_hand == 1
    assert g.same_hand_streak == 1


def test_update_combo_loss_resets():
    g = _make_game()
    g.combo = 5
    g.last_hand = 0
    g.same_hand_streak = 5
    g._update_combo(False, 0)
    assert g.combo == 0
    assert g.last_hand == -1
    assert g.same_hand_streak == 0


# ── _update_ai_prediction ──
def test_ai_prediction_empty_history():
    g = _make_game()
    g.player_history = []
    g.ai_hp = 10
    g._update_ai_prediction()
    assert 0 <= g.ai_prediction <= 2


def test_ai_prediction_deterministic():
    g = _make_game(42)
    g.player_history = [0, 0, 0, 1, 2, 0, 0, 1]
    g.ai_hp = 10
    g._update_ai_prediction()
    assert g.ai_prediction == 0  # most frequent


def test_ai_prediction_tight_window():
    g = _make_game(42)
    g.player_history = [0, 0, 2, 2, 1, 1, 0, 1, 2, 2]
    g.ai_hp = 3  # window=4
    g._update_ai_prediction()
    recent = g.player_history[-4:]  # [1, 0, 2, 2]
    counts = [0, 0, 0]
    for h in recent:
        counts[h] += 1
    most_freq = max(range(3), key=lambda i: counts[i])
    assert g.ai_prediction == most_freq


# ── _get_damage_multiplier ──
def test_damage_multiplier_normal():
    g = _make_game()
    g.combo = 1
    g.super_mode = False
    assert g._get_damage_multiplier() == 1.0


def test_damage_multiplier_combo2():
    g = _make_game()
    g.combo = 2
    g.super_mode = False
    assert g._get_damage_multiplier() == 1.5


def test_damage_multiplier_combo6():
    g = _make_game()
    g.combo = 6
    g.super_mode = False
    assert g._get_damage_multiplier() == 2.0


def test_damage_multiplier_super():
    g = _make_game()
    g.super_mode = True
    assert g._get_damage_multiplier() == 3.0


# ── _fill_queue ──
def test_fill_queue():
    g = _make_game()
    g.queue = []
    g._fill_queue()
    assert len(g.queue) == Game.QUEUE_SIZE
    for h in g.queue:
        assert 0 <= h <= 2


def test_fill_queue_partial():
    g = _make_game()
    g.queue = [0]
    g._fill_queue()
    assert len(g.queue) == Game.QUEUE_SIZE


# ── _replace_hand_at ──
def test_replace_hand_at():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.queue = [0, 1, 2]
    g.energy = 3
    result = g._replace_hand_at(1)
    assert result is True
    assert len(g.queue) == Game.QUEUE_SIZE
    assert g.energy == 2


def test_replace_hand_at_no_energy():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.queue = [0, 1, 2]
    g.energy = 0
    result = g._replace_hand_at(1)
    assert result is False
    assert g.queue == [0, 1, 2]


def test_replace_hand_at_wrong_phase():
    g = _make_game()
    g.phase = Phase.TITLE
    g.queue = [0, 1, 2]
    g.energy = 3
    result = g._replace_hand_at(1)
    assert result is False


def test_replace_hand_at_out_of_bounds():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.queue = [0, 1, 2]
    g.energy = 3
    assert g._replace_hand_at(-1) is False
    assert g._replace_hand_at(3) is False


# ── reset ──
def test_reset():
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.max_combo = 3
    g.ai_hp = 3
    g.player_hp = 1
    g.high_score = 500
    g.player_history = [0, 1, 2, 0, 1]
    g.ai_history = [1, 0, 2]
    g.super_mode = True
    g.super_timer = 3
    g.turn_count = 10
    g.particles = [Particle(0, 0, 0, 0, 5, RED)]
    g.energy = 1

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.ai_hp == Game.AI_MAX_HP
    assert g.player_hp == Game.PLAYER_MAX_HP
    assert g.high_score == 500
    assert g.player_history == []
    assert g.ai_history == []
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.turn_count == 0
    assert len(g.queue) == Game.QUEUE_SIZE
    assert g.energy == Game.MAX_ENERGY
    assert len(g.particles) == 0


# ── Particle system ──
def test_spawn_particles():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, WHITE, 5)
    assert len(g.particles) == 5


def test_update_particles_lifecycle():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, WHITE, 2)
    g.particles[0].life = 1
    g.particles[1].life = 2
    g._update_particles()
    assert len(g.particles) == 1


# ── SUPER MODE ──
def test_super_mode_trigger():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.current_player_hand = 0
    g.current_ai_hand = 2
    g.combo = 3
    g.last_hand = 0
    g.same_hand_streak = 3
    g.max_combo = 3
    g.super_mode = False
    g.ai_hp = 10
    g.player_hp = 5
    g.energy = 2
    g.queue = [0, 1, 1]
    g.score = 0

    g._process_result()

    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION
    assert g.combo >= Game.COMBO_SUPER_THRESHOLD


def test_super_mode_does_3x_damage():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.current_player_hand = 0
    g.current_ai_hand = 2
    g.combo = 4
    g.super_mode = True
    g.super_timer = 5
    g.last_hand = 0
    g.same_hand_streak = 4
    g.max_combo = 4
    g.ai_hp = 10
    g.player_hp = 5
    g.energy = 2
    g.queue = [0, 1, 1]
    g.score = 0

    g._process_result()

    assert g.ai_hp == 7  # 10 - 3*1
    assert g.score == 3
    assert g.player_hp == 5


def test_super_mode_beats_everything():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.current_player_hand = 0  # ROCK
    g.current_ai_hand = 1  # PAPER (beats ROCK normally)
    g.combo = 0
    g.super_mode = True
    g.super_timer = 5
    g.last_hand = -1
    g.ai_hp = 10
    g.player_hp = 5
    g.energy = 2
    g.queue = [0, 1, 1]
    g.score = 0

    g._process_result()

    assert g.ai_hp == 7  # Super mode beats PAPER (normally would lose)
    assert g.score == 3


def test_super_timer_decrements():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 3

    g._do_super_tick()
    assert g.super_timer == 2
    assert g.super_mode is True

    g._do_super_tick()
    assert g.super_timer == 1

    g._do_super_tick()
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.combo == 0


# ── Energy ──
def test_energy_regenerates():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.current_player_hand = 0
    g.current_ai_hand = 2
    g.combo = 0
    g.last_hand = -1
    g.energy = 1
    g.ai_hp = 10
    g.player_hp = 5
    g.queue = [0, 1, 1]
    g.score = 0

    g._process_result()

    assert g.energy == 2  # 1 + 1 (regeneration)


def test_energy_capped():
    g = _make_game()
    g.phase = Phase.QUEUE
    g.current_player_hand = 0
    g.current_ai_hand = 2
    g.combo = 0
    g.last_hand = -1
    g.energy = Game.MAX_ENERGY
    g.ai_hp = 10
    g.player_hp = 5
    g.queue = [0, 1, 1]
    g.score = 0

    g._process_result()

    assert g.energy == Game.MAX_ENERGY  # capped


# ── Dataclass ──
def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-0.5, life=15, color=RED)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == RED


# ── Game class attributes ──
def test_game_class_attrs():
    assert Game.AI_MAX_HP == 10
    assert Game.PLAYER_MAX_HP == 5
    assert Game.MAX_ENERGY == 3
    assert Game.COMBO_SUPER_THRESHOLD == 4
    assert Game.SUPER_DURATION == 5
    assert Game.QUEUE_SIZE == 3
