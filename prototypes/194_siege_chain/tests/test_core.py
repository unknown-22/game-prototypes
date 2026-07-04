from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (  # type: ignore[import-untyped]
    BASE_SCORE,
    COMBO_FOR_SUPER,
    COLORS,
    GAME_DURATION,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_PER_MISMATCH,
    MAX_PARTICLES,
    SUPER_DURATION,
    SUPER_SCORE_MULT,
    Block,
    Boulder,
    Game,
    Phase,
    Particle,
    TrajectoryPoint,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.AIMING
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.super_mode = False
    g.super_flash = 0
    g.game_timer = GAME_DURATION
    g.blocks = []
    g.boulder = None
    g.particles = []
    g.floating_texts = []
    g.aim_start_x = 0
    g.aim_start_y = 0
    g.aiming = False
    g.impact_pause = 0
    g.prev_trajectory = []
    g.color_index = 0
    g.frame = 0
    g._phase_playing_start = True
    g._init_wall()
    return g


# ═══════════════════════════════════════════════════════════════
# Wall initialization
# ═══════════════════════════════════════════════════════════════


def test_wall_has_all_blocks() -> None:
    g = _make_game()
    assert len(g.blocks) == 48  # 8 cols * 6 rows


def test_wall_blocks_have_valid_colors() -> None:
    g = _make_game()
    for b in g.blocks:
        assert b.color in COLORS


def test_wall_blocks_have_valid_positions() -> None:
    g = _make_game()
    cols = {b.col for b in g.blocks}
    rows = {b.row for b in g.blocks}
    assert cols == set(range(8))
    assert rows == set(range(6))


# ═══════════════════════════════════════════════════════════════
# Color cycling
# ═══════════════════════════════════════════════════════════════


def test_get_next_color_cycles() -> None:
    g = _make_game()
    colors = [g._get_next_color() for _ in range(8)]
    assert colors == [COLORS[0], COLORS[1], COLORS[2], COLORS[3], COLORS[0], COLORS[1], COLORS[2], COLORS[3]]


# ═══════════════════════════════════════════════════════════════
# Wall collision
# ═══════════════════════════════════════════════════════════════


def test_check_wall_collision_hits_block() -> None:
    g = _make_game()
    block = g.blocks[0]
    bx = 140 + block.col * 24 + 12
    by = 40 + block.row * 24 + 12
    hit = g._check_wall_collision(bx, by)
    assert hit is block


def test_check_wall_collision_misses_empty_area() -> None:
    g = _make_game()
    hit = g._check_wall_collision(10, 10)
    assert hit is None


def test_check_wall_collision_ignores_dead_blocks() -> None:
    g = _make_game()
    block = g.blocks[0]
    block.hp = 0
    bx = 140 + block.col * 24 + 12
    by = 40 + block.row * 24 + 12
    hit = g._check_wall_collision(bx, by)
    assert hit is None


# ═══════════════════════════════════════════════════════════════
# Impact: matching color
# ═══════════════════════════════════════════════════════════════


def test_matching_color_builds_combo() -> None:
    g = _make_game()
    block = g.blocks[0]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=block.color)
    g._handle_impact(block)
    assert g.combo == 1
    assert g.score > 0
    assert block.hp == 0
    assert block.cracked is True


def test_matching_color_consecutive_builds_combo() -> None:
    g = _make_game()
    # Find two blocks with same color
    color = COLORS[0]
    same_color_blocks = [b for b in g.blocks if b.color == color]
    assert len(same_color_blocks) >= 2
    b1 = same_color_blocks[0]
    b2 = same_color_blocks[1]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
    g._handle_impact(b1)
    assert g.combo == 1
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
    g._handle_impact(b2)
    assert g.combo == 2


def test_matching_color_score_scales_with_combo() -> None:
    g = _make_game()
    color = COLORS[0]
    blocks = [b for b in g.blocks if b.color == color]
    scores = []
    for i, block in enumerate(blocks[:4]):
        g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
        g._handle_impact(block)
        scores.append(g.score)
    assert scores[0] < scores[1] < scores[2] < scores[3]


# ═══════════════════════════════════════════════════════════════
# Impact: mismatching color
# ═══════════════════════════════════════════════════════════════


def test_mismatching_color_resets_combo() -> None:
    g = _make_game()
    # Build combo first
    color = COLORS[0]
    blocks = [b for b in g.blocks if b.color == color]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
    g._handle_impact(blocks[0])
    assert g.combo == 1

    # Mismatch
    other_color = COLORS[1]
    other_blocks = [b for b in g.blocks if b.color == other_color]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
    g._handle_impact(other_blocks[0])
    assert g.combo == 0


def test_mismatching_color_adds_heat() -> None:
    g = _make_game()
    block = g.blocks[0]
    wrong_color = COLORS[0] if block.color != COLORS[0] else COLORS[1]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=wrong_color)
    g._handle_impact(block)
    assert g.heat == HEAT_PER_MISMATCH


def test_mismatching_color_gives_base_score() -> None:
    g = _make_game()
    block = g.blocks[0]
    wrong_color = COLORS[0] if block.color != COLORS[0] else COLORS[1]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=wrong_color)
    score_before = g.score
    g._handle_impact(block)
    assert g.score == score_before + 5


# ═══════════════════════════════════════════════════════════════
# SUPER mode
# ═══════════════════════════════════════════════════════════════


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    color = COLORS[0]
    blocks = [b for b in g.blocks if b.color == color]
    for block in blocks[:COMBO_FOR_SUPER]:
        g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
        g._handle_impact(block)
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_any_color_builds_combo() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    block = g.blocks[0]
    any_color = COLORS[0] if block.color != COLORS[0] else COLORS[1]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=any_color)
    g._handle_impact(block)
    assert g.combo == 1
    assert block.hp == 0


def test_super_mode_gives_3x_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    block = g.blocks[0]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=COLORS[0])
    score_before = g.score
    g._handle_impact(block)
    score_after = g.score
    # In super mode, score = BASE_SCORE * SUPER_SCORE_MULT * (1 + combo * 0.5)
    assert score_after > score_before
    assert score_after == score_before + int(BASE_SCORE * SUPER_SCORE_MULT * (1 + 1 * 0.5))


def test_super_mode_ends_after_duration() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


# ═══════════════════════════════════════════════════════════════
# HEAT system
# ═══════════════════════════════════════════════════════════════


def test_heat_decays_over_time() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX - 5
    block = g.blocks[0]
    wrong_color = COLORS[0] if block.color != COLORS[0] else COLORS[1]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=wrong_color)
    g._handle_impact(block)
    assert g.heat <= HEAT_MAX


# ═══════════════════════════════════════════════════════════════
# CA crack propagation
# ═══════════════════════════════════════════════════════════════


def test_crack_propagation_hits_same_color_adjacent() -> None:
    g = _make_game()
    g.blocks.clear()
    # Create two adjacent blocks with same color
    b1 = Block(col=0, row=0, color=COLORS[0], hp=1)
    b2 = Block(col=1, row=0, color=COLORS[0], hp=1)
    g.blocks.extend([b1, b2])
    g._crack_neighbors(b1)
    assert b2.hp == 0
    assert b2.cracked is True


def test_crack_propagation_does_not_hit_different_color() -> None:
    g = _make_game()
    g.blocks.clear()
    b1 = Block(col=0, row=0, color=COLORS[0], hp=1)
    b2 = Block(col=1, row=0, color=COLORS[1], hp=1)
    g.blocks.extend([b1, b2])
    g._crack_neighbors(b1)
    assert b2.hp == 1
    assert b2.cracked is False


def test_super_mode_crack_propagates_to_any_color() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.blocks.clear()
    b1 = Block(col=0, row=0, color=COLORS[0], hp=1)
    b2 = Block(col=1, row=0, color=COLORS[1], hp=1)
    g.blocks.extend([b1, b2])
    g._crack_neighbors(b1)
    assert b2.hp == 0
    assert b2.cracked is True


def test_crack_propagation_hits_4_directions() -> None:
    g = _make_game()
    g.blocks.clear()
    center = Block(col=1, row=1, color=COLORS[0], hp=1)
    up = Block(col=1, row=0, color=COLORS[0], hp=1)
    down = Block(col=1, row=2, color=COLORS[0], hp=1)
    left = Block(col=0, row=1, color=COLORS[0], hp=1)
    right = Block(col=2, row=1, color=COLORS[0], hp=1)
    g.blocks.extend([center, up, down, left, right])
    g._crack_neighbors(center)
    for b in [up, down, left, right]:
        assert b.hp == 0, f"Block at ({b.col}, {b.row}) was not cracked"
        assert b.cracked is True


def test_crack_propagation_skips_diagonal() -> None:
    g = _make_game()
    g.blocks.clear()
    center = Block(col=1, row=1, color=COLORS[0], hp=1)
    diagonal = Block(col=2, row=2, color=COLORS[0], hp=1)
    g.blocks.extend([center, diagonal])
    g._crack_neighbors(center)
    assert diagonal.hp == 1
    assert diagonal.cracked is False


def test_propagate_cracks_continues_chain() -> None:
    g = _make_game()
    g.blocks.clear()
    b1 = Block(col=0, row=0, color=COLORS[0], hp=0, cracked=True, crack_timer=8)
    b2 = Block(col=1, row=0, color=COLORS[0], hp=1)
    b3 = Block(col=2, row=0, color=COLORS[0], hp=1)
    g.blocks.extend([b1, b2, b3])
    g._propagate_cracks()
    assert b2.hp == 0 and b2.cracked is True
    # b3 is not cracked yet because b2 was just cracked in this propagation step
    # Next call would crack b3


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


def test_spawn_match_particles_creates_particles() -> None:
    g = _make_game()
    g._spawn_match_particles(100, 100, COLORS[0])
    assert len(g.particles) > 0
    assert all(p.color == COLORS[0] for p in g.particles)


def test_spawn_super_particles_creates_more() -> None:
    g = _make_game()
    g._spawn_match_particles(100, 100, COLORS[0])
    n_normal = len(g.particles)
    g.particles.clear()
    g._spawn_super_particles(100, 100)
    n_super = len(g.particles)
    assert n_super > n_normal


def test_particles_update_moves_and_decays() -> None:
    g = _make_game()
    g._spawn_match_particles(100, 100, COLORS[0])
    initial_lives = [p.life for p in g.particles]
    g._update_particles()
    for i, p in enumerate(g.particles):
        assert p.life == initial_lives[i] - 1


def test_particles_max_limit() -> None:
    g = _make_game()
    for _ in range(MAX_PARTICLES + 10):
        g._spawn_match_particles(100, 100, COLORS[0])
    assert len(g.particles) <= MAX_PARTICLES


# ═══════════════════════════════════════════════════════════════
# Floating text
# ═══════════════════════════════════════════════════════════════


def test_floating_text_moves_up_and_fades() -> None:
    g = _make_game()
    g._add_floating_text(100, 100, "+10", COLORS[0])
    y_before = g.floating_texts[0].y
    life_before = g.floating_texts[0].life
    g._update_floating_texts()
    assert g.floating_texts[0].y < y_before
    assert g.floating_texts[0].life == life_before - 1


def test_floating_text_expired_removed() -> None:
    g = _make_game()
    g._add_floating_text(100, 100, "+10", COLORS[0])
    g.floating_texts[0].life = 0
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════
# Miss shot
# ═══════════════════════════════════════════════════════════════


def test_miss_shot_resets_combo() -> None:
    g = _make_game()
    g.combo = 3
    g._miss_shot()
    assert g.combo == 0
    assert g.boulder is None
    assert g.phase == Phase.AIMING


# ═══════════════════════════════════════════════════════════════
# Score / Max combo tracking
# ═══════════════════════════════════════════════════════════════


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    color = COLORS[0]
    blocks = [b for b in g.blocks if b.color == color]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
    g._handle_impact(blocks[0])
    assert g.max_combo == 1
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=color)
    g._handle_impact(blocks[1])
    assert g.max_combo == 2
    # Mismatch resets combo but max stays
    other_color = COLORS[1]
    other_blocks = [b for b in g.blocks if b.color == other_color]
    # Use a boulder color different from the block's color to force mismatch
    mismatch_color = COLORS[2] if other_blocks[0].color != COLORS[2] else COLORS[3]
    g.boulder = Boulder(x=0, y=0, vx=0, vy=0, color=mismatch_color)
    g._handle_impact(other_blocks[0])
    assert g.combo == 0
    assert g.max_combo == 2


# ═══════════════════════════════════════════════════════════════
# Reset
# ═══════════════════════════════════════════════════════════════


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50
    g.boulder = Boulder(x=10, y=10, vx=1, vy=1, color=COLORS[0])
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, life=10, color=COLORS[0]))
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.boulder is None
    assert len(g.particles) == 0
    assert len(g.blocks) == 48


def test_reset_reinitializes_wall() -> None:
    g = _make_game()
    # Destroy all blocks
    for b in g.blocks:
        b.hp = 0
    g.blocks.clear()
    g.reset()
    assert len(g.blocks) == 48
    for b in g.blocks:
        assert b.hp == 1
        assert b.color in COLORS


# ═══════════════════════════════════════════════════════════════
# Game over conditions
# ═══════════════════════════════════════════════════════════════


def test_game_over_when_timer_expires() -> None:
    g = _make_game()
    g.game_timer = 0
    g.phase = Phase.AIMING
    g._update_playing_common()
    assert g.phase == Phase.GAME_OVER


def test_all_blocks_destroyed_bonus() -> None:
    g = _make_game()
    g.score = 100
    g.blocks.clear()
    g.game_timer = 0
    g._update_playing_common()
    assert g.score == 150  # 100 * 1.5


def test_high_score_updated() -> None:
    g = _make_game()
    g.score = 500
    g.high_score = 0
    g.game_timer = 0
    g.phase = Phase.AIMING
    g._update_playing_common()
    assert g.high_score == 500


# ═══════════════════════════════════════════════════════════════
# Trajectory
# ═══════════════════════════════════════════════════════════════


def test_trajectory_points_stored() -> None:
    g = _make_game()
    g.prev_trajectory.clear()
    g.phase = Phase.FLYING
    g.boulder = Boulder(x=50, y=200, vx=3, vy=-5, color=COLORS[0])
    initial_count = len(g.prev_trajectory)
    g._update_flying()
    assert len(g.prev_trajectory) > initial_count


def test_trajectory_max_limit() -> None:
    g = _make_game()
    g.prev_trajectory = [TrajectoryPoint(x=0, y=0) for _ in range(300)]
    g.phase = Phase.FLYING
    g.boulder = Boulder(x=50, y=200, vx=3, vy=-5, color=COLORS[0])
    g._update_flying()
    assert len(g.prev_trajectory) <= 300

    # When boulder misses (y > SCREEN_H + 20 or x > SCREEN_W + 20 or x < -20)
    # we transition to AIMING phase

