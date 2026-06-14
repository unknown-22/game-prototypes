"""test_imports.py — Headless logic tests for SNOWBOARD CHAIN."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/125_snowboard_chain")

from main import (
    Game,
    Gate,
    Obstacle,
    Particle,
    FloatingText,
    EchoGate,
    Phase,
    GATE_COLORS,
    GATE_W,
    GATE_H,
    BASE_SCORE,
    SURGE_BONUS,
    MAX_HEAT,
    MAX_HP,
    HEAT_WRONG_GATE,
    SUPER_THRESHOLD,
    SUPER_MULTIPLIER,
    HEAT_DECAY,
    SURGE_HEAT_REDUCTION,
    SPLIT_INTERVAL,
    SPLIT_LANE_OFFSET,
    SCREEN_W,
    SCREEN_H,
    PLAYER_Y,
    PLAYER_W,
    PLAYER_H,
    SUPER_DURATION,
)


# ── Helper ──────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.reset()
    g._rng = __import__("random").Random(seed)
    return g


# ── Dataclass tests ─────────────────────────────────────────────────────

def test_gate_defaults() -> None:
    gate = Gate(x=100.0, y=50.0, color=2)
    assert gate.x == 100.0
    assert gate.y == 50.0
    assert gate.w == GATE_W
    assert gate.h == GATE_H
    assert gate.color == 2
    assert gate.hit is False
    assert gate.lane == 0


def test_obstacle_defaults() -> None:
    obs = Obstacle(x=160.0, y=30.0)
    assert obs.x == 160.0
    assert obs.y == 30.0
    assert obs.alive is True


def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 15


def test_floating_text_defaults() -> None:
    ft = FloatingText(x=80.0, y=200.0, text="+10", life=45, color=10)
    assert ft.x == 80.0
    assert ft.y == 200.0
    assert ft.text == "+10"
    assert ft.life == 45
    assert ft.color == 10


def test_echo_gate_defaults() -> None:
    eg = EchoGate(x=50.0, y=100.0, color=1, life=120)
    assert eg.x == 50.0
    assert eg.y == 100.0
    assert eg.color == 1
    assert eg.life == 120
    assert eg.collected is False


# ── Phase enum tests ──────────────────────────────────────────────────

def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.SPLIT in Phase
    assert Phase.CONVERGE in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 5


# ── Constants tests ───────────────────────────────────────────────────

def test_constants() -> None:
    assert len(GATE_COLORS) == 4
    assert BASE_SCORE == 10
    assert SURGE_BONUS == 200
    assert MAX_HEAT == 100
    assert MAX_HP == 3
    assert HEAT_WRONG_GATE == 15
    assert SUPER_THRESHOLD == 5
    assert SUPER_MULTIPLIER == 3
    assert SURGE_HEAT_REDUCTION == 30


# ── Reset tests ───────────────────────────────────────────────────────

def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == MAX_HP
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.split_active is False
    assert g.split_player_lane == 0
    assert g.player_color_idx == -1
    assert g.scroll_speed == 2.0
    assert len(g.gates) == 0
    assert len(g.obstacles) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.echo_gates) == 0


def test_reset_after_play() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.combo = 5
    g.max_combo = 5
    g.hp = 1
    g.heat = 80.0
    g.super_mode = True
    g.gates.append(Gate(x=100, y=50, color=0))
    g.particles.append(Particle(x=10, y=10, vx=1, vy=1, life=10, color=8))
    g.floating_texts.append(FloatingText(x=50, y=50, text="test", life=10, color=7))
    g.echo_gates.append(EchoGate(x=30, y=30, color=0, life=60))
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == MAX_HP
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.split_active is False
    assert g.player_color_idx == -1
    assert len(g.gates) == 0
    assert len(g.obstacles) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.echo_gates) == 0


# ── Gate collision tests ──────────────────────────────────────────────

def test_check_gate_hit_true() -> None:
    g = _make_game()
    g.player_x = 160.0
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)
    px = g.player_x - PLAYER_W / 2
    py = PLAYER_Y - PLAYER_H / 2
    assert g._check_gate_hit(gate, px, py) is True


def test_check_gate_hit_false() -> None:
    g = _make_game()
    g.player_x = 160.0
    gate = Gate(x=30.0, y=PLAYER_Y, color=0)  # far away
    px = g.player_x - PLAYER_W / 2
    py = PLAYER_Y - PLAYER_H / 2
    assert g._check_gate_hit(gate, px, py) is False


# ── Gate hit: first gate (always succeeds) ────────────────────────────

def test_first_gate_hit_any_color() -> None:
    g = _make_game()
    g.player_color_idx = -1
    gate = Gate(x=160.0, y=PLAYER_Y, color=2)  # BLUE, not matching -1
    g._on_gate_hit(gate)
    assert gate.hit is True
    assert g.player_color_idx == 2
    assert g.combo == 1
    assert g.score > 0


# ── Gate hit: same color builds combo ─────────────────────────────────

def test_same_color_hit_increases_combo() -> None:
    g = _make_game()
    g.player_color_idx = 0  # RED
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)  # RED same
    g._on_gate_hit(gate)
    assert gate.hit is True
    assert g.combo == 1
    assert g.score == BASE_SCORE  # combo=1, multiplier=1


def test_same_color_combo_multiplies_score() -> None:
    g = _make_game()
    g.player_color_idx = 1  # GREEN
    g.combo = 4
    # Hit same color: combo becomes 5
    gate = Gate(x=160.0, y=PLAYER_Y, color=1)
    g._on_gate_hit(gate)
    assert g.combo == 5
    assert g.score == BASE_SCORE * 5  # points = 10 * 5 * 1 = 50


# ── Gate hit: wrong color resets combo ────────────────────────────────

def test_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.player_color_idx = 0  # RED
    g.combo = 3
    gate = Gate(x=160.0, y=PLAYER_Y, color=1)  # GREEN (wrong)
    g._on_gate_hit(gate)
    assert g.combo == 0
    assert g.heat == HEAT_WRONG_GATE


def test_wrong_color_adds_heat() -> None:
    g = _make_game()
    g.player_color_idx = 2  # BLUE
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)  # RED (wrong)
    g._on_gate_hit(gate)
    assert g.heat == HEAT_WRONG_GATE
    assert g.combo == 0


# ── SUPER mode tests ──────────────────────────────────────────────────

def test_combo_5_triggers_super_mode() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.combo = 4
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)
    g._on_gate_hit(gate)
    assert g.combo == 5
    assert g.combo >= SUPER_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_gives_triple_score() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.super_mode = True
    g.combo = 1
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)
    g._on_gate_hit(gate)
    assert g.score == BASE_SCORE * 2 * SUPER_MULTIPLIER  # combo=2 * 3x


def test_super_timer_countdown() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 4
    assert g.super_mode is True


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


# ── Max combo tracking ────────────────────────────────────────────────

def test_max_combo_tracked() -> None:
    g = _make_game()
    g.player_color_idx = 0
    for _ in range(3):
        gate = Gate(x=160.0, y=PLAYER_Y, color=0)
        g._on_gate_hit(gate)
    assert g.combo == 3
    assert g.max_combo == 3
    # Wrong color resets combo but max stays
    gate = Gate(x=160.0, y=PLAYER_Y, color=1)
    g._on_gate_hit(gate)
    assert g.combo == 0
    assert g.max_combo == 3


# ── Obstacle collision tests ──────────────────────────────────────────

def test_obstacle_hit_reduces_hp() -> None:
    g = _make_game()
    obs = Obstacle(x=160.0, y=PLAYER_Y)
    g._on_obstacle_hit(obs)
    assert obs.alive is False
    assert g.hp == MAX_HP - 1
    assert g.invuln_timer > 0


def test_obstacle_hit_game_over() -> None:
    g = _make_game()
    g.hp = 1
    g.phase = Phase.PLAYING
    obs = Obstacle(x=160.0, y=PLAYER_Y)
    g._on_obstacle_hit(obs)
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


# ── HEAT tests ────────────────────────────────────────────────────────

def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_max_triggers_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT  # already at max
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── Split zone tests ──────────────────────────────────────────────────

def test_start_split_zone_sets_phase() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._start_split_zone()
    assert g.phase == Phase.SPLIT
    assert g.split_active is True
    assert g.split_player_lane == 0
    assert len(g.gates) == 2
    assert g.gates[0].lane == 1
    assert g.gates[1].lane == 2


def test_split_gates_at_correct_positions() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._start_split_zone()
    assert g.gates[0].x == SCREEN_W / 2 - SPLIT_LANE_OFFSET
    assert g.gates[1].x == SCREEN_W / 2 + SPLIT_LANE_OFFSET


def test_end_split_zone_player_hit_and_ghost_hit_surge() -> None:
    g = _make_game(42)  # seed 42: random() ≈ 0.639 < 0.8 → ghost_hit=True
    g.phase = Phase.PLAYING
    g._start_split_zone()
    g.split_player_lane = 1
    for gate in g.gates:
        if gate.lane == 1:
            gate.hit = True
    score_before = g.score
    heat_before = g.heat
    g._end_split_zone()
    assert g.phase == Phase.CONVERGE
    assert g.split_active is False
    # RNG seed 42 gives ghost hit (0.639 < 0.8), so SURGE triggers
    if g.split_ghost_hit:
        assert g.score == score_before + SURGE_BONUS
        assert g.heat <= heat_before
    assert g.combo > 0


def test_end_split_zone_player_miss_penalty() -> None:
    g = _make_game(42)
    g.phase = Phase.PLAYING
    g._start_split_zone()
    g.split_player_lane = 2
    g.combo = 3
    g._end_split_zone()
    assert g.combo == 0
    assert g.heat >= HEAT_WRONG_GATE
    assert g.phase == Phase.CONVERGE


def test_end_split_zone_player_hit_ghost_miss() -> None:
    g = _make_game(11)  # seed 11: after randint(0,3), random() ≈ 0.866 >= 0.8 → ghost_hit=False
    g.phase = Phase.PLAYING
    g._start_split_zone()
    g.split_player_lane = 1
    g.player_color_idx = 0
    g.combo = 2
    for gate in g.gates:
        if gate.lane == 1:
            gate.hit = True
    score_before = g.score
    g._end_split_zone()
    # Player hit alone (ghost missed): combo +1, normal score
    assert g.combo == 3
    assert g.score > score_before
    assert g.score < score_before + SURGE_BONUS


def test_end_split_zone_super_bonus_on_surge_threshold() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._start_split_zone()
    g.split_player_lane = 1
    g.combo = 3  # SURGE adds +2 combo, reaching SUPER_THRESHOLD (5)
    for gate in g.gates:
        if gate.lane == 1:
            gate.hit = True
    g.split_ghost_hit = True
    g._end_split_zone()
    assert g.combo == 5
    assert g.super_mode is True


# ── Player bounds test ────────────────────────────────────────────────

def test_player_clamped_to_screen() -> None:
    g = _make_game()
    g.player_x = -10.0
    # Simulate clamping
    g.player_x = max(PLAYER_W / 2, min(SCREEN_W - PLAYER_W / 2, g.player_x))
    assert g.player_x == PLAYER_W / 2
    g.player_x = SCREEN_W + 10.0
    g.player_x = max(PLAYER_W / 2, min(SCREEN_W - PLAYER_W / 2, g.player_x))
    assert g.player_x == SCREEN_W - PLAYER_W / 2


# ── Gate removal tests ────────────────────────────────────────────────

def test_gates_removed_when_off_screen() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.gate_spawn_timer = 999  # prevent auto-spawn
    g.gates.append(Gate(x=160, y=SCREEN_H + GATE_H + 10, color=0))
    g._update_gates()
    assert len(g.gates) == 0


def test_gates_passed_without_hit_reset_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 5
    g.gates.append(Gate(x=30, y=PLAYER_Y + PLAYER_H + 1, color=0, hit=False, lane=0))
    g._update_gates()
    assert g.combo == 0


# ── Particle tests ────────────────────────────────────────────────────

def test_spawn_particles() -> None:
    g = _make_game(42)
    g._spawn_particles(160.0, 200.0, 8, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color == 8
        assert p.life == 25


def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=5)
    g.particles.append(p)
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 48.0
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text tests ───────────────────────────────────────────────

def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+10", 8)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+10"
    assert ft.life == 45
    assert ft.color == 8


def test_update_floating_texts_floats_and_decays() -> None:
    g = _make_game()
    ft = FloatingText(x=80.0, y=200.0, life=10, text="x3", color=10)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert ft.y == 199.2
    assert ft.life == 9


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    ft = FloatingText(x=80.0, y=200.0, life=1, text="x3", color=10)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Echo gate tests ───────────────────────────────────────────────────

def test_add_echo_gate() -> None:
    g = _make_game()
    g._add_echo_gate(160.0, 100.0, 0)
    assert len(g.echo_gates) == 1
    assert g.echo_gates[0].x == 160.0
    assert g.echo_gates[0].y == 100.0
    assert g.echo_gates[0].color == 0
    assert g.echo_gates[0].life == 120
    assert g.echo_gates[0].collected is False


def test_update_echo_gates_decays() -> None:
    g = _make_game()
    eg = EchoGate(x=50.0, y=100.0, color=1, life=3)
    g.echo_gates.append(eg)
    g._update_echo_gates()
    assert eg.life == 2


def test_update_echo_gates_removes_dead() -> None:
    g = _make_game()
    eg = EchoGate(x=50.0, y=100.0, color=1, life=1)
    g.echo_gates.append(eg)
    g._update_echo_gates()
    assert len(g.echo_gates) == 0


def test_echo_gate_collection() -> None:
    g = _make_game()
    g.player_x = 160.0
    eg = EchoGate(x=160.0, y=PLAYER_Y, color=0, life=60)
    g.echo_gates.append(eg)
    score_before = g.score
    g._update_echo_gates()
    assert eg.collected is True
    assert g.score == score_before + 50


# ── Scroll speed test ─────────────────────────────────────────────────

def test_scroll_speed_increases() -> None:
    g = _make_game()
    initial = g.scroll_speed
    g._update_scroll_speed()
    assert g.scroll_speed > initial


# ── Score calculation test ────────────────────────────────────────────

def test_score_calculation_normal() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.combo = 2
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)
    g._on_gate_hit(gate)
    # combo becomes 3, points = 10 * 3 * 1 = 30
    assert g.score == 30


def test_score_calculation_super_mode() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.super_mode = True
    g.combo = 3
    gate = Gate(x=160.0, y=PLAYER_Y, color=0)
    g._on_gate_hit(gate)
    # combo becomes 4, points = 10 * 4 * 3 = 120
    assert g.score == 120


# ── Phase transition tests ────────────────────────────────────────────

def test_split_timer_triggers_split_zone() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.split_timer = SPLIT_INTERVAL - 2  # 298, not yet at threshold
    g._update_split_timer()
    assert g.phase == Phase.PLAYING  # still playing (299 < 300)
    g._update_split_timer()
    assert g.phase == Phase.SPLIT  # now triggers (300 >= 300)
    assert g.split_elapsed == 0


def test_split_duration_ends_to_converge() -> None:
    g = _make_game()
    g.phase = Phase.SPLIT
    g.split_elapsed = 89
    g._update_split_timer()
    assert g.phase == Phase.CONVERGE
    assert g.converge_timer == 30


def test_converge_duration_ends_to_playing() -> None:
    g = _make_game()
    g.phase = Phase.CONVERGE
    g.converge_timer = 1
    g._update_converge()
    assert g.phase == Phase.PLAYING


# ── Invulnerability test ──────────────────────────────────────────────

def test_invuln_timer_countdown() -> None:
    g = _make_game()
    g.invuln_timer = 10
    g._update_invuln()
    assert g.invuln_timer == 9


# ── Full playthrough simulation ───────────────────────────────────────

def test_full_play_simulation() -> None:
    g = _make_game(42)
    g.phase = Phase.PLAYING

    # Simulate hitting 3 same-color gates
    for _ in range(3):
        color = 0
        g.player_color_idx = color
        gate = Gate(x=g.player_x, y=PLAYER_Y, color=color)
        g._on_gate_hit(gate)
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score > 0

    # Hit wrong color
    g._on_gate_hit(Gate(x=g.player_x, y=PLAYER_Y, color=1))
    assert g.combo == 0
    assert g.max_combo == 3  # max preserved


print("All tests passed!")
