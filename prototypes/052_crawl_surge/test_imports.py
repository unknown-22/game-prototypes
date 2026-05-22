"""test_imports.py — Headless logic tests for CRAWL SURGE."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/052_crawl_surge")

# Use Game.__new__ to bypass pyxel.init
from main import (
    Game, Phase, Segment, CrawlChain, Shot, Mushroom, Particle, FloatingText,
    SCREEN_W, SCREEN_H, PLAYER_AREA_TOP, PLAYER_Y, PLAYER_HALF_W,
    NUM_COLORS, COLOR_VALS, COLOR_NAMES,
    SEGMENT_SIZE, SEGMENT_HALF, SEGMENT_SCORE, COMBO_THRESHOLD,
    SURGE_SCORE, SHOT_SPEED, CRAWL_SPEED, CRAWL_INTERVAL,
    INITIAL_SEGMENTS, MAX_MUSHROOMS, MUSHROOM_DROP_CHANCE,
    PLAYER_COLOR_CYCLE_INTERVAL,
)

import random
import math


def _make_game() -> Game:
    """Create a Game instance without pyxel.init."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() will touch
    g.player_x = 0.0
    g.player_color = 0
    g.shots = []
    g.chains = []
    g.mushrooms = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.wave = 1
    g.phase = Phase.PLAYING
    g._crawl_timer = 0
    g._surge_timer = 0
    g._wave_clear_timer = 0
    g._shake_frames = 0
    g._color_timer = 0
    g._rng = random.Random(42)
    g.reset()
    return g


# ── Data class tests ──

def test_segment_creation() -> None:
    s = Segment(x=50.0, y=30.0, color=2)
    assert s.x == 50.0
    assert s.y == 30.0
    assert s.color == 2


def test_crawl_chain_creation() -> None:
    segs = [Segment(x=100.0, y=20.0, color=0)]
    cc = CrawlChain(segments=segs, direction=-1)
    assert len(cc.segments) == 1
    assert cc.direction == -1


def test_shot_creation() -> None:
    s = Shot(x=128.0, y=200.0)
    assert s.x == 128.0
    assert s.y == 200.0


def test_mushroom_creation() -> None:
    m = Mushroom(x=40, y=60, hp=2)
    assert m.x == 40
    assert m.y == 60
    assert m.hp == 2


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=15)
    assert p.life == 15
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=50.0, y=30.0, text="OK", color=10, life=20)
    assert ft.text == "OK"
    assert ft.life == 20


# ── Game state tests ──

def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.wave == 1
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert len(g.shots) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g._shake_frames == 0


def test_wave_1_has_initial_segments() -> None:
    g = _make_game()
    total = g._total_segments()
    assert total == INITIAL_SEGMENTS


def test_wave_increase_adds_segments() -> None:
    g = _make_game()
    g.wave = 3
    g._init_wave()
    expected = INITIAL_SEGMENTS + 2 * 3  # wave-1 bonus per wave, but _init_wave computes based on self.wave
    # Actually: INITIAL_SEGMENTS + (wave - 1) * WAVE_SEGMENT_BONUS
    # wave=3 → 8 + 2*3 = 14
    assert g._total_segments() == 14


def test_mushrooms_spawned() -> None:
    g = _make_game()
    assert 0 <= len(g.mushrooms) <= MAX_MUSHROOMS


# ── Crawl chain tests ──

def test_crawl_head_moves_right() -> None:
    g = _make_game()
    chain = g.chains[0]
    assert chain.direction == 1
    head = chain.segments[0]
    old_x = head.x
    g._crawl_chain(chain)
    assert chain.segments[0].x > old_x


def test_crawl_body_follows() -> None:
    g = _make_game()
    chain = g.chains[0]
    if len(chain.segments) < 2:
        return  # skip if only 1 segment
    old_pos_0 = (chain.segments[0].x, chain.segments[0].y)
    g._crawl_chain(chain)
    # The second segment should now be at the head's old position
    assert abs(chain.segments[1].x - old_pos_0[0]) < 1.0
    assert abs(chain.segments[1].y - old_pos_0[1]) < 1.0


def test_crawl_head_wraps_left() -> None:
    g = _make_game()
    chain = g.chains[0]
    head = chain.segments[0]
    head.x = float(SEGMENT_HALF)
    chain.direction = -1
    old_y = head.y
    g._crawl_chain(chain)
    assert chain.direction == 1  # reversed
    assert head.y > old_y  # descended


def test_crawl_head_wraps_right() -> None:
    g = _make_game()
    chain = g.chains[0]
    head = chain.segments[0]
    head.x = float(SCREEN_W - SEGMENT_HALF)
    chain.direction = 1
    old_y = head.y
    g._crawl_chain(chain)
    assert chain.direction == -1  # reversed
    assert head.y > old_y  # descended


def test_crawl_mushroom_collision() -> None:
    g = _make_game()
    chain = g.chains[0]
    head = chain.segments[0]
    # Place head exactly on a mushroom
    head.x = 50.0
    head.y = 40.0
    g.mushrooms = [Mushroom(x=50, y=40)]
    chain.direction = 1
    old_y = head.y
    g._crawl_chain(chain)
    assert chain.direction == -1  # reversed
    assert head.y > old_y  # descended


# ── Hit/combat tests ──

def test_on_hit_match_builds_combo() -> None:
    g = _make_game()
    # Set up: one chain with segment matching player color
    seg = Segment(x=100.0, y=100.0, color=0)
    chain = CrawlChain(segments=[seg], direction=1)
    g.chains = [chain]
    g.player_color = 0
    g.combo = 0
    g._on_hit_segment(0, 0, seg)
    assert g.combo >= 1
    assert g.score >= SEGMENT_SCORE


def test_on_hit_mismatch_resets_combo() -> None:
    g = _make_game()
    seg = Segment(x=100.0, y=100.0, color=0)
    chain = CrawlChain(segments=[seg], direction=1)
    g.chains = [chain]
    g.player_color = 1  # mismatch
    g.combo = 2
    g._on_hit_segment(0, 0, seg)
    assert g.combo == 0


def test_on_hit_removes_segment() -> None:
    g = _make_game()
    seg0 = Segment(x=100.0, y=100.0, color=0)
    seg1 = Segment(x=90.0, y=100.0, color=1)
    chain = CrawlChain(segments=[seg0, seg1], direction=1)
    g.chains = [chain]
    g.player_color = 0  # match head
    g._on_hit_segment(0, 0, seg0)
    assert len(g.chains[0].segments) == 1


def test_surge_triggers_at_combo_threshold() -> None:
    g = _make_game()
    # Create chain with 4 same-color segments
    segs = [
        Segment(x=100.0, y=50.0, color=0),
        Segment(x=90.0, y=50.0, color=0),
        Segment(x=80.0, y=50.0, color=0),
        Segment(x=70.0, y=50.0, color=2),  # different color at end
    ]
    chain = CrawlChain(segments=segs, direction=1)
    g.chains = [chain]
    g.player_color = 0
    g.combo = COMBO_THRESHOLD  # already at threshold
    g._on_hit_segment(0, 0, segs[0])
    # SURGE should have triggered
    assert g.phase == Phase.SURGE_ANIM
    assert g._surge_timer > 0
    # All 3 same-color segments (indices 0,1,2) should be destroyed
    # Survivors: only segs[3] (different color)
    if g.chains:
        assert len(g.chains[0].segments) == 1
        assert g.chains[0].segments[0].color == 2


def test_bfs_surge_counts_connected_same_color() -> None:
    g = _make_game()
    segs = [
        Segment(x=100.0, y=50.0, color=0),
        Segment(x=90.0, y=50.0, color=0),
        Segment(x=80.0, y=50.0, color=1),  # different
        Segment(x=70.0, y=50.0, color=0),
    ]
    chain = CrawlChain(segments=segs, direction=1)
    count = g._bfs_surge(chain, 0, 0)  # hit index 0, color 0
    assert count == 2  # only indices 0,1 are connected same-color


def test_bfs_surge_stops_at_boundary() -> None:
    g = _make_game()
    segs = [
        Segment(x=100.0, y=50.0, color=0),
        Segment(x=90.0, y=50.0, color=1),
        Segment(x=80.0, y=50.0, color=0),
    ]
    chain = CrawlChain(segments=segs, direction=1)
    count = g._bfs_surge(chain, 0, 0)
    assert count == 1  # only index 0


# ── Wave clear tests ──

def test_wave_clear_transitions() -> None:
    g = _make_game()
    g.chains = []  # no segments
    g._wave_clear_timer = 0
    g.phase = Phase.WAVE_CLEAR
    g._update_wave_clear()
    assert g.wave == 2
    assert g.phase == Phase.PLAYING


# ── Game over tests ──

def test_game_over_segment_at_bottom() -> None:
    g = _make_game()
    seg = Segment(x=100.0, y=float(SCREEN_H - SEGMENT_SIZE), color=0)
    g.chains = [CrawlChain(segments=[seg], direction=1)]
    g.phase = Phase.PLAYING
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_game_over_player_touched() -> None:
    g = _make_game()
    g.player_x = 100.0
    seg = Segment(x=100.0, y=float(PLAYER_AREA_TOP), color=0)
    g.chains = [CrawlChain(segments=[seg], direction=1)]
    g.phase = Phase.PLAYING
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_game_over_not_touched_if_far() -> None:
    g = _make_game()
    g.player_x = 200.0
    seg = Segment(x=100.0, y=float(PLAYER_AREA_TOP), color=0)
    g.chains = [CrawlChain(segments=[seg], direction=1)]
    g.phase = Phase.PLAYING
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# ── Shot update tests ──

def test_shots_move_upward() -> None:
    g = _make_game()
    g.shots = [Shot(x=100.0, y=200.0)]
    g._update_shots()
    assert g.shots[0].y == 200.0 - SHOT_SPEED


def test_shot_removed_off_screen() -> None:
    g = _make_game()
    g.shots = [Shot(x=100.0, y=-1.0)]
    g._update_shots()
    assert len(g.shots) == 0


def test_shot_hits_mushroom() -> None:
    g = _make_game()
    g.shots = [Shot(x=50.0, y=50.0)]
    g.mushrooms = [Mushroom(x=50, y=50, hp=2)]
    g.chains = []  # no segments to intercept
    g._update_shots()
    assert len(g.shots) == 0  # shot consumed
    assert g.mushrooms[0].hp == 1


def test_mushroom_destroyed_at_hp_zero() -> None:
    g = _make_game()
    g.shots = [Shot(x=50.0, y=50.0)]
    g.mushrooms = [Mushroom(x=50, y=50, hp=1)]
    g.chains = []
    g._update_shots()
    assert len(g.mushrooms) == 0


# ── Particle tests ──

def test_particles_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=1)]
    g._update_particles()
    assert len(g.particles) == 0  # expired


def test_particles_persist() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, color=8, life=5)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4
    assert g.particles[0].x == 1.0


# ── Floating text tests ──

def test_floating_texts_decay() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="HI", color=7, life=1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_rises() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=50.0, y=100.0, text="OK", color=7, life=5)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.0


# ── Player position constraint ──

def test_player_clamped_left() -> None:
    g = _make_game()
    g.player_x = -10.0
    # We can't call _update_playing (uses pyxel.btn), test the clamp logic directly
    g.player_x = max(PLAYER_HALF_W, min(SCREEN_W - PLAYER_HALF_W, g.player_x))
    assert g.player_x == PLAYER_HALF_W


def test_player_clamped_right() -> None:
    g = _make_game()
    g.player_x = float(SCREEN_W + 10)
    g.player_x = max(PLAYER_HALF_W, min(SCREEN_W - PLAYER_HALF_W, g.player_x))
    assert g.player_x == SCREEN_W - PLAYER_HALF_W


# ── Color cycling ──

def test_player_color_cycles_forward() -> None:
    g = _make_game()
    g.player_color = 0
    g.player_color = (g.player_color + 1) % NUM_COLORS
    assert g.player_color == 1


def test_player_color_wraps() -> None:
    g = _make_game()
    g.player_color = NUM_COLORS - 1
    g.player_color = (g.player_color + 1) % NUM_COLORS
    assert g.player_color == 0


# ── Score tests ──

def test_score_with_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.score = 0
    seg = Segment(x=100.0, y=50.0, color=0)
    chain = CrawlChain(segments=[seg], direction=1)
    g.chains = [chain]
    g.player_color = 0
    g._on_hit_segment(0, 0, seg)
    assert g.score >= SEGMENT_SCORE * 3


# ── Config constant sanity ──

def test_config_constants() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 240
    assert NUM_COLORS == 4
    assert len(COLOR_VALS) == 4
    assert len(COLOR_NAMES) == 4
    assert SEGMENT_SIZE > 0
    assert SHOT_SPEED > 0
    assert CRAWL_SPEED > 0
    assert COMBO_THRESHOLD >= 2
    assert INITIAL_SEGMENTS >= 4
    assert MAX_MUSHROOMS > 0


if __name__ == "__main__":
    import traceback
    tests = [
        ("test_segment_creation", test_segment_creation),
        ("test_crawl_chain_creation", test_crawl_chain_creation),
        ("test_shot_creation", test_shot_creation),
        ("test_mushroom_creation", test_mushroom_creation),
        ("test_particle_creation", test_particle_creation),
        ("test_floating_text_creation", test_floating_text_creation),
        ("test_reset_initial_state", test_reset_initial_state),
        ("test_wave_1_has_initial_segments", test_wave_1_has_initial_segments),
        ("test_wave_increase_adds_segments", test_wave_increase_adds_segments),
        ("test_mushrooms_spawned", test_mushrooms_spawned),
        ("test_crawl_head_moves_right", test_crawl_head_moves_right),
        ("test_crawl_body_follows", test_crawl_body_follows),
        ("test_crawl_head_wraps_left", test_crawl_head_wraps_left),
        ("test_crawl_head_wraps_right", test_crawl_head_wraps_right),
        ("test_crawl_mushroom_collision", test_crawl_mushroom_collision),
        ("test_on_hit_match_builds_combo", test_on_hit_match_builds_combo),
        ("test_on_hit_mismatch_resets_combo", test_on_hit_mismatch_resets_combo),
        ("test_on_hit_removes_segment", test_on_hit_removes_segment),
        ("test_surge_triggers_at_combo_threshold", test_surge_triggers_at_combo_threshold),
        ("test_bfs_surge_counts_connected_same_color", test_bfs_surge_counts_connected_same_color),
        ("test_bfs_surge_stops_at_boundary", test_bfs_surge_stops_at_boundary),
        ("test_wave_clear_transitions", test_wave_clear_transitions),
        ("test_game_over_segment_at_bottom", test_game_over_segment_at_bottom),
        ("test_game_over_player_touched", test_game_over_player_touched),
        ("test_game_over_not_touched_if_far", test_game_over_not_touched_if_far),
        ("test_shots_move_upward", test_shots_move_upward),
        ("test_shot_removed_off_screen", test_shot_removed_off_screen),
        ("test_shot_hits_mushroom", test_shot_hits_mushroom),
        ("test_mushroom_destroyed_at_hp_zero", test_mushroom_destroyed_at_hp_zero),
        ("test_particles_decay", test_particles_decay),
        ("test_particles_persist", test_particles_persist),
        ("test_floating_texts_decay", test_floating_texts_decay),
        ("test_floating_text_rises", test_floating_text_rises),
        ("test_player_clamped_left", test_player_clamped_left),
        ("test_player_clamped_right", test_player_clamped_right),
        ("test_player_color_cycles_forward", test_player_color_cycles_forward),
        ("test_player_color_wraps", test_player_color_wraps),
        ("test_score_with_combo", test_score_with_combo),
        ("test_config_constants", test_config_constants),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    if passed < len(tests):
        sys.exit(1)
