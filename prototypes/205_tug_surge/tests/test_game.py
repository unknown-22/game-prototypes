import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    COLORS,
    EchoGhost,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = Game.GAME_TIME
    g.super_tug_active = False
    g.super_tug_timer = 0
    g.rope_center = float(Game.ROPE_START_X)
    g.current_flag_color_idx = 0
    g.flag_color_timer = Game.COLOR_CYCLE_FRAMES
    g.resonance_color_idx = None
    g.pull_cooldown = 0
    g.ai_pull_force = 0.5
    g.ai_force_timer = 100
    g.idle_frames = 0
    g.won = False
    g.particles: list = []
    g.floating_texts: list = []
    g.echo_ghosts: list = []
    g._elapsed_time = 0.0
    return g


class TestPull:
    def test_first_pull_sets_resonance(self) -> None:
        g = make_game()
        g.resonance_color_idx = None
        g.current_flag_color_idx = 0
        combo_inc, score_gained = g._pull()
        assert combo_inc is False
        assert g.combo == 0
        assert g.heat == Game.HEAT_PULL
        assert g.resonance_color_idx == 0
        assert score_gained == 0

    def test_same_color_combo_up(self) -> None:
        g = make_game()
        g.resonance_color_idx = 0
        g.current_flag_color_idx = 0
        combo_inc, score_gained = g._pull()
        assert combo_inc is True
        assert g.combo == 1
        assert score_gained > 0
        assert g.resonance_color_idx == 0

    def test_different_color_resets_combo(self) -> None:
        g = make_game()
        g.combo = 3
        g.resonance_color_idx = 0
        g.current_flag_color_idx = 1
        combo_inc, score_gained = g._pull()
        assert combo_inc is False
        assert g.combo == 0
        assert g.heat >= Game.HEAT_PULL + Game.HEAT_WRONG

    def test_score_increases_with_combo(self) -> None:
        g = make_game()
        g.resonance_color_idx = 0
        g.current_flag_color_idx = 0
        g.combo = 2
        combo_inc, score_gained = g._pull()
        assert combo_inc is True
        expected = int(Game.SCORE_BASE * (1 + 3 * 0.5))
        assert score_gained == expected

    def test_pull_cooldown_blocks(self) -> None:
        g = make_game()
        g.pull_cooldown = 10
        combo_inc, score_gained = g._pull()
        assert combo_inc is False
        assert score_gained == 0


class TestSuperTug:
    def test_super_tug_activates_at_combo_4(self) -> None:
        g = make_game()
        g.combo = 3
        g.resonance_color_idx = 0
        g.current_flag_color_idx = 0
        g._pull()
        assert g.super_tug_active is True
        assert g.super_tug_timer == Game.SUPER_TUG_DURATION
        assert g.combo == 4

    def test_super_tug_pull_any_color_counts(self) -> None:
        g = make_game()
        g.super_tug_active = True
        g.super_tug_timer = 200
        g.current_flag_color_idx = 2
        g.resonance_color_idx = 0
        g.combo = 5
        combo_inc, score_gained = g._pull()
        assert combo_inc is True
        assert g.combo == 6

    def test_super_tug_ends(self) -> None:
        g = make_game()
        g.super_tug_active = True
        g.super_tug_timer = 1
        g._update_super_tug()
        assert g.super_tug_active is False
        assert g.super_tug_timer == 0


class TestRope:
    def test_rope_starts_at_center(self) -> None:
        g = make_game()
        assert g.rope_center == Game.ROPE_START_X

    def test_rope_moves_right_on_pull(self) -> None:
        g = make_game()
        g.rope_center = 160.0
        g.ai_pull_force = 0.0
        g._update_rope(1.0)
        assert g.rope_center > 160.0

    def test_rope_clamped_at_right_win(self) -> None:
        g = make_game()
        g.rope_center = 1000.0
        g._update_rope(1.0)
        assert g.rope_center == Game.RIGHT_WIN_X

    def test_rope_clamped_at_left_lose(self) -> None:
        g = make_game()
        g.rope_center = -100.0
        g._update_rope(1.0)
        assert g.rope_center == Game.LEFT_LOSE_X


class TestWinLose:
    def test_win_when_rope_past_right(self) -> None:
        g = make_game()
        g.rope_center = float(Game.RIGHT_WIN_X)
        result = g._check_win_lose()
        assert result is True
        assert g.won is True
        assert g.phase == Phase.GAME_OVER

    def test_lose_when_rope_past_left(self) -> None:
        g = make_game()
        g.rope_center = float(Game.LEFT_LOSE_X)
        result = g._check_win_lose()
        assert result is True
        assert g.won is False
        assert g.phase == Phase.GAME_OVER

    def test_lose_when_heat_max(self) -> None:
        g = make_game()
        g.heat = Game.HEAT_MAX
        result = g._check_win_lose()
        assert result is True
        assert g.won is False

    def test_not_end_in_middle(self) -> None:
        g = make_game()
        g.rope_center = 160.0
        g.heat = 50.0
        result = g._check_win_lose()
        assert result is False
        assert g.phase == Phase.PLAYING


class TestHeat:
    def test_heat_decay_idle(self) -> None:
        g = make_game()
        g.heat = 50.0
        g.idle_frames = Game.IDLE_THRESHOLD + 1
        g._update_heat()
        assert g.heat == 50.0 - Game.HEAT_DECAY_IDLE

    def test_heat_decay_super(self) -> None:
        g = make_game()
        g.super_tug_active = True
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0 - Game.HEAT_DECAY_SUPER

    def test_heat_does_not_decay_below_zero(self) -> None:
        g = make_game()
        g.heat = 0.0
        g.idle_frames = Game.IDLE_THRESHOLD + 1
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_not_decay_when_active(self) -> None:
        g = make_game()
        g.heat = 50.0
        g.idle_frames = 10
        g._update_heat()
        assert g.heat == 50.0


class TestFlagColor:
    def test_flag_color_cycles(self) -> None:
        g = make_game()
        assert g.current_flag_color_idx == 0
        g.flag_color_timer = 1
        g._update_flag_color()
        assert g.current_flag_color_idx == 1
        assert g.flag_color_timer > 0

    def test_flag_color_wraps(self) -> None:
        g = make_game()
        g.current_flag_color_idx = len(COLORS) - 1
        g.flag_color_timer = 1
        g._update_flag_color()
        assert g.current_flag_color_idx == 0


class TestAI:
    def test_ai_force_changes_when_timer_expires(self) -> None:
        g = make_game()
        g.ai_force_timer = 0
        g._update_ai()
        assert g.ai_force_timer > 0
        assert 0.0 <= g.ai_pull_force <= 1.5

    def test_ai_force_not_change_if_timer_active(self) -> None:
        g = make_game()
        g.ai_pull_force = 0.5
        g.ai_force_timer = 50
        g._update_ai()
        assert g.ai_force_timer == 49
        assert g.ai_pull_force == 0.5


class TestEchoGhosts:
    def test_echo_ghost_added_on_combo_pull(self) -> None:
        g = make_game()
        g.resonance_color_idx = 0
        g.current_flag_color_idx = 0
        assert len(g.echo_ghosts) == 0
        g._pull()
        assert len(g.echo_ghosts) == 1
        assert g.echo_ghosts[0].life == Game.GHOST_LIFE

    def test_echo_ghost_not_added_on_first_pull(self) -> None:
        g = make_game()
        g.resonance_color_idx = None
        g.current_flag_color_idx = 0
        g._pull()
        assert len(g.echo_ghosts) == 0

    def test_echo_ghosts_decay(self) -> None:
        g = make_game()
        g.echo_ghosts = [
            EchoGhost(rope_pos=100.0, life=3, color=8),
            EchoGhost(rope_pos=120.0, life=0, color=3),
            EchoGhost(rope_pos=140.0, life=2, color=5),
        ]
        g._update_echos()
        assert len(g.echo_ghosts) == 2

    def test_echo_ghosts_max_limit(self) -> None:
        g = make_game()
        for i in range(Game.MAX_ECHOS + 10):
            g.echo_ghosts.append(EchoGhost(rope_pos=float(i), life=100, color=8))
        g._update_echos()
        assert len(g.echo_ghosts) <= Game.MAX_ECHOS


class TestParticles:
    def test_particles_decay(self) -> None:
        g = make_game()
        g.particles = [
            Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=3, color=8),
            Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=3),
            Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=5),
        ]
        g._update_particles()
        assert len(g.particles) == 2

    def test_particles_move(self) -> None:
        g = make_game()
        g.particles = [
            Particle(x=100.0, y=100.0, vx=2.0, vy=1.0, life=10, color=8),
        ]
        g._update_particles()
        assert g.particles[0].x == 102.0
        assert g.particles[0].y == 101.0
        assert g.particles[0].vy == 1.1

    def test_particles_max_limit(self) -> None:
        g = make_game()
        for i in range(Game.MAX_PARTICLES + 50):
            g.particles.append(
                Particle(x=float(i), y=0.0, vx=0.0, vy=0.0, life=10, color=8)
            )
        g._update_particles()
        assert len(g.particles) <= Game.MAX_PARTICLES


class TestFloatingTexts:
    def test_floating_texts_decay(self) -> None:
        g = make_game()
        g.floating_texts = [
            FloatingText(x=0.0, y=0.0, text="A", life=3, color=7),
            FloatingText(x=0.0, y=0.0, text="B", life=0, color=7),
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1

    def test_floating_texts_move_up(self) -> None:
        g = make_game()
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="test", life=10, color=7),
        ]
        g._update_floating_texts()
        assert g.floating_texts[0].y < 100.0

    def test_floating_texts_max_limit(self) -> None:
        g = make_game()
        for i in range(Game.MAX_FLOATING_TEXTS + 10):
            g.floating_texts.append(
                FloatingText(x=0.0, y=0.0, text="x", life=10, color=7)
            )
        g._update_floating_texts()
        assert len(g.floating_texts) <= Game.MAX_FLOATING_TEXTS


class TestReset:
    def test_reset_clears_state(self) -> None:
        g = make_game()
        g.score = 500
        g.combo = 3
        g.max_combo = 4
        g.heat = 60.0
        g.timer = 100
        g.super_tug_active = True
        g.super_tug_timer = 50
        g.rope_center = 200.0
        g.particles = [Particle(x=0, y=0, vx=1, vy=1, life=10, color=8)]
        g.floating_texts = [FloatingText(x=0, y=0, text="t", life=10, color=7)]
        g.echo_ghosts = [EchoGhost(rope_pos=100.0, life=50, color=8)]

        g.reset()

        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.timer == Game.GAME_TIME
        assert g.super_tug_active is False
        assert g.super_tug_timer == 0
        assert g.rope_center == Game.ROPE_START_X
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert len(g.echo_ghosts) == 0


class TestStartGame:
    def test_start_game_sets_playing_state(self) -> None:
        g = make_game()
        g.phase = Phase.TITLE
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.timer == Game.GAME_TIME
        assert g.rope_center == Game.ROPE_START_X


class TestMaxCombo:
    def test_max_combo_tracks_highest(self) -> None:
        g = make_game()
        g.resonance_color_idx = None
        g.current_flag_color_idx = 0
        g._pull()
        g.pull_cooldown = 0
        g.resonance_color_idx = 0
        g.current_flag_color_idx = 0
        g._pull()
        g.pull_cooldown = 0
        g._pull()
        g.pull_cooldown = 0
        g._pull()
        assert g.max_combo == 3
        g.current_flag_color_idx = 1
        g.pull_cooldown = 0
        g._pull()
        assert g.combo == 0
        assert g.max_combo == 3
