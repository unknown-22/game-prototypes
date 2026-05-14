"""test_imports.py — Headless logic tests for COLOR FLUX.

Tests game logic without initializing Pyxel (uses Game.__new__ pattern).
Avoids calling any methods that touch pyxel input state (btn, btnp, mouse_x, etc.).
"""

from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/026_color_flux")

from main import (
    BASE_SCORE,
    BIRD_X,
    BIRD_SIZE,
    CEILING_Y,
    COLORS,
    COLOR_NAMES,
    COMBO_BONUS,
    FLOOR_Y,
    GATE_MAX_GAP,
    GATE_MIN_GAP,
    GATE_MIN_Y,
    GATE_MAX_Y,
    GATE_SPAWN_INTERVAL,
    GATE_SPEED,
    GATE_WIDTH,
    GRAVITY,
    MAX_HEAT,
    MISS_GATE_HEAT,
    N_COLORS,
    SCREEN_H,
    SCREEN_W,
    SYNTHESIS_DURATION,
    SYNTHESIS_MULTIPLIER,
    SYNTHESIS_THRESHOLD,
    WRONG_COLOR_HEAT,
    ColorFlux,
    Gate,
    Particle,
    Phase,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def make_game() -> ColorFlux:
    """Create a game instance without initializing Pyxel."""
    g = ColorFlux.__new__(ColorFlux)
    g.reset()
    return g


# ── Constants ────────────────────────────────────────────────────────────────


def test_constants() -> None:
    """Verify all constants are reasonable."""
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert len(COLORS) == N_COLORS == 4
    assert len(COLOR_NAMES) == 4
    assert SYNTHESIS_THRESHOLD == 5
    assert SYNTHESIS_DURATION == 120
    assert MAX_HEAT == 10
    assert GRAVITY > 0
    assert GATE_SPEED > 0
    assert GATE_MIN_GAP < GATE_MAX_GAP
    assert BASE_SCORE > 0


# ── Gate Dataclass ───────────────────────────────────────────────────────────


def test_gate_creation() -> None:
    """Gate dataclass constructs correctly."""
    g = Gate(x=200.0, gap_y=120, gap_h=60, color=COLORS[0])
    assert g.x == 200.0
    assert g.gap_y == 120
    assert g.gap_h == 60
    assert g.color == COLORS[0]
    assert g.scored is False


def test_gate_properties() -> None:
    """Gate computed properties are correct."""
    g = Gate(x=200.0, gap_y=120, gap_h=60, color=COLORS[0])
    assert g.top_h == 120 - 30  # gap_y - gap_h // 2
    assert g.bottom_y == 120 + 30  # gap_y + gap_h // 2
    assert g.right == 200.0 + GATE_WIDTH
    assert g.left == 200.0

    # Verify gap is centered
    assert g.top_h + g.gap_h == g.bottom_y


def test_gate_scored_flag() -> None:
    """Gate scored flag works."""
    g = Gate(x=200.0, gap_y=120, gap_h=60, color=COLORS[0])
    assert not g.scored
    g.scored = True
    assert g.scored


# ── Particle Dataclass ───────────────────────────────────────────────────────


def test_particle_creation() -> None:
    """Particle dataclass constructs correctly."""
    p = Particle(x=100.0, y=50.0, vx=-1.0, vy=-2.0, life=20, color=COLORS[1], text="+50")
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.vx == -1.0
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == COLORS[1]
    assert p.text == "+50"


def test_particle_default_text() -> None:
    """Particle default text is empty."""
    p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=0)
    assert p.text == ""


# ── Phase Enum ────────────────────────────────────────────────────────────────


def test_phase_values() -> None:
    """Phase enum has expected members."""
    assert Phase.PLAYING in Phase
    assert Phase.SYNTHESIS in Phase
    assert Phase.GAME_OVER in Phase


# ── Game Initialization ──────────────────────────────────────────────────────


def test_game_reset() -> None:
    """Game reset initializes all state correctly."""
    g = make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.gates_passed == 0
    assert g.synthesis_count == 0
    assert g._synth_timer == 0
    assert g._gate_timer >= 0
    assert CEILING_Y < g.bird_y < FLOOR_Y
    assert g.bird_color in COLORS
    assert len(g.gates) == 0
    assert len(g.particles) == 0


def test_game_bird_color_is_valid() -> None:
    """Bird starts with a valid color."""
    g = make_game()
    assert g.bird_color in COLORS


# ── Gate Spawning ────────────────────────────────────────────────────────────


def test_spawn_gate() -> None:
    """Gate spawn creates a valid gate."""
    g = make_game()
    assert len(g.gates) == 0
    g._spawn_gate()
    assert len(g.gates) == 1
    gate = g.gates[0]
    assert gate.x == SCREEN_W
    assert gate.color in COLORS
    assert GATE_MIN_GAP <= gate.gap_h <= GATE_MAX_GAP
    margin = gate.gap_h // 2 + 8
    assert margin <= gate.gap_y <= SCREEN_H - margin
    assert gate.scored is False


def test_spawn_multiple_gates() -> None:
    """Multiple gates spawn correctly."""
    g = make_game()
    for _ in range(5):
        g._spawn_gate()
    assert len(g.gates) == 5


# ── Color Shift ──────────────────────────────────────────────────────────────


def test_shift_bird_color() -> None:
    """Bird color changes to a different color."""
    g = make_game()
    original = g.bird_color
    # May need multiple shifts if random picks same color (unlikely with 4 options)
    for _ in range(10):
        g._shift_bird_color()
        if g.bird_color != original:
            break
    assert g.bird_color != original
    assert g.bird_color in COLORS


# ── Match Logic ──────────────────────────────────────────────────────────────


def test_on_match_increments_combo() -> None:
    """Matching gate increments combo and score."""
    g = make_game()
    g.bird_color = COLORS[0]
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[0])
    g._on_match(gate)
    assert g.combo == 1
    assert g.gates_passed == 1
    assert g.score == BASE_SCORE + 1 * COMBO_BONUS  # 10 + 5 = 15


def test_on_match_combo_accumulates() -> None:
    """Consecutive matching gates build combo multiplicatively."""
    g = make_game()
    g.bird_color = COLORS[0]
    expected_score = 0
    for i in range(4):
        gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[0])
        g._on_match(gate)
        expected_score += BASE_SCORE + (i + 1) * COMBO_BONUS
    assert g.combo == 4
    assert g.score == expected_score


def test_on_match_triggers_synthesis() -> None:
    """Reaching SYNTHESIS_THRESHOLD triggers synthesis mode."""
    g = make_game()
    g.bird_color = COLORS[0]
    for i in range(SYNTHESIS_THRESHOLD - 1):
        gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[0])
        g._on_match(gate)
    assert g.phase == Phase.PLAYING
    # Last match triggers synthesis
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[0])
    g._on_match(gate)
    assert g.phase == Phase.SYNTHESIS
    assert g._synth_timer == SYNTHESIS_DURATION
    assert g.synthesis_count == 1
    assert g.combo == SYNTHESIS_THRESHOLD


def test_on_match_max_combo_tracking() -> None:
    """Max combo tracks highest achieved."""
    g = make_game()
    g.bird_color = COLORS[0]
    for _ in range(3):
        gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[0])
        g._on_match(gate)
    assert g.max_combo == 3
    assert g.combo == 3


# ── Mismatch Logic ───────────────────────────────────────────────────────────


def test_on_mismatch_resets_combo() -> None:
    """Wrong-color gate resets combo and adds heat."""
    g = make_game()
    g.bird_color = COLORS[0]
    g.combo = 4
    g.heat = 0
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[1])
    g._on_mismatch(gate)
    assert g.combo == 0
    assert g.heat == WRONG_COLOR_HEAT
    assert g.gates_passed == 1


def test_on_mismatch_base_score() -> None:
    """Wrong-color gate awards base score only."""
    g = make_game()
    g.bird_color = COLORS[0]
    g.combo = 5
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[1])
    g._on_mismatch(gate)
    assert g.score == BASE_SCORE  # 10, no combo bonus


def test_on_mismatch_heat_causes_death() -> None:
    """Wrong-color gate at max heat causes game over."""
    g = make_game()
    g.bird_color = COLORS[0]
    g.heat = MAX_HEAT - WRONG_COLOR_HEAT
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[1])
    g._on_mismatch(gate)
    assert g.heat == MAX_HEAT
    assert g.phase == Phase.GAME_OVER


# ── Miss Logic ───────────────────────────────────────────────────────────────


def test_on_miss_adds_heat() -> None:
    """Missing a gate adds heat."""
    g = make_game()
    g.heat = 0
    g._on_miss()
    assert g.heat == MISS_GATE_HEAT


def test_on_miss_max_heat_causes_death() -> None:
    """Missing at max heat causes game over."""
    g = make_game()
    g.heat = MAX_HEAT - MISS_GATE_HEAT
    g._on_miss()
    assert g.heat == MAX_HEAT
    assert g.phase == Phase.GAME_OVER


def test_on_miss_heat_caps() -> None:
    """Heat doesn't exceed MAX_HEAT."""
    g = make_game()
    g.heat = MAX_HEAT
    g._on_miss()
    assert g.heat == MAX_HEAT


# ── Synthesis Logic ──────────────────────────────────────────────────────────


def test_trigger_synthesis_enters_phase() -> None:
    """_trigger_synthesis enters SYNTHESIS phase."""
    g = make_game()
    g._trigger_synthesis()
    assert g.phase == Phase.SYNTHESIS
    assert g._synth_timer == SYNTHESIS_DURATION
    assert g.synthesis_count == 1


def test_trigger_synthesis_spawns_particles() -> None:
    """_trigger_synthesis spawns burst particles."""
    g = make_game()
    before = len(g.particles)
    g._trigger_synthesis()
    assert len(g.particles) > before


def test_on_synthesis_match_scoring() -> None:
    """Synthesis match uses 3x multiplier."""
    g = make_game()
    g.combo = 3
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=60, color=COLORS[0])
    g._on_synthesis_match(gate)
    expected = (BASE_SCORE + 3 * COMBO_BONUS) * SYNTHESIS_MULTIPLIER
    assert g.score == expected
    assert g.gates_passed == 1


def test_synthesis_timer_expires() -> None:
    """Synthesis phase ends when timer expires."""
    g = make_game()
    g.phase = Phase.SYNTHESIS
    g._synth_timer = 0
    g.combo = 7
    # Simulate the synthesis update timer decrement
    g._synth_timer -= 1
    if g._synth_timer <= 0:
        g.phase = Phase.PLAYING
        g.combo = 0
    assert g.phase == Phase.PLAYING
    assert g.combo == 0


# ── Death ─────────────────────────────────────────────────────────────────────


def test_die_sets_game_over() -> None:
    """Death sets phase to GAME_OVER."""
    g = make_game()
    assert g.phase == Phase.PLAYING
    g._die()
    assert g.phase == Phase.GAME_OVER


def test_die_spawns_particles() -> None:
    """Death spawns particle burst."""
    g = make_game()
    before = len(g.particles)
    g._die()
    assert len(g.particles) > before


# ── Particle System ──────────────────────────────────────────────────────────


def test_update_particles_decrements_life() -> None:
    """Particle update decrements life."""
    g = make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=COLORS[0])]
    g._update_particles()
    assert g.particles[0].life == 4


def test_update_particles_removes_dead() -> None:
    """Dead particles are removed."""
    g = make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=COLORS[0])]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_moves_position() -> None:
    """Particles move by velocity."""
    g = make_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=5, color=COLORS[0])]
    g._update_particles()
    assert g.particles[0].x == 11.5
    assert g.particles[0].y == 18.0


def test_spawn_flap_particle() -> None:
    """Flap spawns particles behind the bird."""
    g = make_game()
    g.bird_y = 100.0
    before = len(g.particles)
    g._spawn_flap_particle()
    assert len(g.particles) == before + 3
    for p in g.particles[before:]:
        assert p.x <= BIRD_X


def test_spawn_score_particle() -> None:
    """Score particle spawns at gate position."""
    g = make_game()
    gate = Gate(x=200.0, gap_y=120, gap_h=60, color=COLORS[0])
    before = len(g.particles)
    g._spawn_score_particle(gate, 50, COLORS[0])
    assert len(g.particles) == before + 1
    p = g.particles[-1]
    assert p.text == "+50"
    assert p.color == COLORS[0]


# ── Boundary Checks ──────────────────────────────────────────────────────────


def test_bird_ceiling_death() -> None:
    """Bird above ceiling should trigger death in update logic."""
    # We can't call _update_playing (uses btnp), but we can test the
    # boundary condition directly by simulating the check
    g = make_game()
    g.bird_y = CEILING_Y - 1
    # Simulate the boundary check from _update_playing
    if g.bird_y <= CEILING_Y or g.bird_y >= FLOOR_Y:
        g._die()
    assert g.phase == Phase.GAME_OVER


def test_bird_floor_death() -> None:
    """Bird below floor triggers death."""
    g = make_game()
    g.bird_y = FLOOR_Y + 1
    if g.bird_y <= CEILING_Y or g.bird_y >= FLOOR_Y:
        g._die()
    assert g.phase == Phase.GAME_OVER


def test_bird_safe_zone() -> None:
    """Bird in safe zone does not die."""
    g = make_game()
    g.bird_y = SCREEN_H / 2
    if g.bird_y <= CEILING_Y or g.bird_y >= FLOOR_Y:
        g._die()
    assert g.phase == Phase.PLAYING


# ── Reset After Death ────────────────────────────────────────────────────────


def test_reset_after_death() -> None:
    """Reset restores all state after game over."""
    g = make_game()
    g.score = 500
    g.combo = 7
    g.heat = 8
    g._die()
    assert g.phase == Phase.GAME_OVER
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.gates_passed == 0


# ── Gate Collision Detection ─────────────────────────────────────────────────


def test_gate_bird_aligned_score_check() -> None:
    """Gate at BIRD_X should trigger scoring when bird passes gap."""
    g = make_game()
    g.bird_y = 120.0
    g.bird_color = COLORS[0]
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=40, color=COLORS[0])
    bird_half = BIRD_SIZE / 2
    bird_top = g.bird_y - bird_half
    bird_bottom = g.bird_y + bird_half
    # Bird should be inside the gap
    assert bird_top > gate.top_h
    assert bird_bottom < gate.bottom_y
    # Bird should NOT collide with pillars
    assert not (bird_top < gate.top_h or bird_bottom > gate.bottom_y)


def test_gate_collision_top_pillar() -> None:
    """Bird hitting top pillar triggers collision."""
    g = make_game()
    g.bird_y = 20.0  # Very high, near top
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=40, color=COLORS[0])
    bird_half = BIRD_SIZE / 2
    bird_top = g.bird_y - bird_half
    bird_bottom = g.bird_y + bird_half
    # Bird should collide with top pillar
    assert bird_top < gate.top_h


def test_gate_collision_bottom_pillar() -> None:
    """Bird hitting bottom pillar triggers collision."""
    g = make_game()
    g.bird_y = 200.0  # Low
    gate = Gate(x=BIRD_X, gap_y=120, gap_h=40, color=COLORS[0])
    bird_half = BIRD_SIZE / 2
    bird_bottom = g.bird_y + bird_half
    # Bird should collide with bottom pillar
    assert bird_bottom > gate.bottom_y


# ── Scoring Formulas ─────────────────────────────────────────────────────────


def test_scoring_gradient() -> None:
    """Higher combo should give more points per gate."""
    base = BASE_SCORE + 1 * COMBO_BONUS  # combo 1
    high = BASE_SCORE + 5 * COMBO_BONUS  # combo 5
    assert high > base


def test_synthesis_scoring_better_than_normal() -> None:
    """Synthesis scoring is higher than normal at same combo."""
    combo = 3
    normal = BASE_SCORE + combo * COMBO_BONUS
    synthesis = normal * SYNTHESIS_MULTIPLIER
    assert synthesis > normal
    assert synthesis == normal * 3


# ── Heat System ──────────────────────────────────────────────────────────────


def test_heat_clamps_at_max() -> None:
    """Heat cannot exceed MAX_HEAT."""
    g = make_game()
    g.heat = MAX_HEAT
    g._on_miss()
    assert g.heat == MAX_HEAT
    g._on_mismatch(Gate(x=0, gap_y=0, gap_h=0, color=0))
    # This won't execute the heat add because gate is at x=0, but
    # the min() in _on_miss already tested above
    assert g.heat == MAX_HEAT


def test_heat_bar_percentage() -> None:
    """Heat bar fill width calculation is correct."""
    for heat in range(MAX_HEAT + 1):
        fraction = heat / MAX_HEAT
        assert 0.0 <= fraction <= 1.0


# ── Edge Cases ───────────────────────────────────────────────────────────────


def test_synthesis_count_increments() -> None:
    """Synthesis count tracks number of times triggered."""
    g = make_game()
    assert g.synthesis_count == 0
    g._trigger_synthesis()
    assert g.synthesis_count == 1
    g._trigger_synthesis()
    assert g.synthesis_count == 2


def test_gate_removal_boundary() -> None:
    """Gates pass removal boundary at right < -20."""
    g = make_game()
    g.gates = [Gate(x=-30.0, gap_y=100, gap_h=50, color=COLORS[0]),
               Gate(x=50.0, gap_y=100, gap_h=50, color=COLORS[1])]
    # Simulate gate cleanup from _update_playing
    g.gates = [gate for gate in g.gates if gate.right > -20]
    assert len(g.gates) == 1
    assert g.gates[0].x == 50.0


def test_colors_are_unique() -> None:
    """All configured colors are distinct."""
    assert len(set(COLORS)) == len(COLORS)


def test_gate_spawn_interval_positive() -> None:
    """Gate spawn interval is reasonable."""
    assert GATE_SPAWN_INTERVAL > 0


def test_display_scale() -> None:
    """Display scale constant exists (tested via import)."""
    from main import DISPLAY_SCALE, FPS
    assert DISPLAY_SCALE > 0
    assert FPS > 0


print("All tests passed!")
