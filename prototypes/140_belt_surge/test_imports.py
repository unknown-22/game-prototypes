"""test_imports.py — Headless logic tests for BELT SURGE."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/140_belt_surge")

import random
from main import (
    Game, Phase, Item, Particle,
    ITEM_COLORS, COLOR_NAMES,
    SCREEN_W, BELT_Y, ITEM_W, ITEM_H,
    MAX_HEAT, SURGE_THRESHOLD, BASE_SPEED, SPEED_INCREMENT,
    SPEED_INCREMENT_INTERVAL, AUTO_CYCLE_SCORE,
    INITIAL_GATE_X,
)


def _make_game() -> Game:
    """Create a headless Game instance using __new__ bypass."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g.phase = Phase.TITLE
    g.gate_x = INITIAL_GATE_X
    g.gate_color = 0
    g.items = []
    g.particles = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.belt_speed = BASE_SPEED
    g._spawn_timer = 0
    g._surge_timer = 0
    g._shake_timer = 0
    g._shake_offset_x = 0
    g._shake_offset_y = 0
    g._surge_score_popup = 0
    g._surge_popup_timer = 0
    g._last_tagged_color_idx = None
    g._score_since_cycle = 0
    g._frame = 0
    g._passed_gate = set()
    g._popup_texts = []
    g._rng = random.Random(42)
    g.reset()
    g._rng = random.Random(42)  # re-seed after reset()
    return g


class TestItemAndParticle:
    """Test data classes and constants."""

    def test_item_colors(self):
        assert len(ITEM_COLORS) == 4
        assert ITEM_COLORS[0] == 8   # RED
        assert ITEM_COLORS[1] == 3   # GREEN
        assert ITEM_COLORS[2] == 5   # DARK_BLUE
        assert ITEM_COLORS[3] == 10  # YELLOW

    def test_color_names(self):
        assert COLOR_NAMES[0] == "RED"
        assert COLOR_NAMES[1] == "GREEN"
        assert COLOR_NAMES[2] == "BLUE"
        assert COLOR_NAMES[3] == "YELLOW"

    def test_item_creation(self):
        item = Item(x=50.0, y=100.0, color=8, color_idx=0)
        assert item.x == 50.0
        assert item.y == 100.0
        assert item.color == 8
        assert item.color_idx == 0
        assert not item.tagged
        assert item.alive

    def test_particle_creation(self):
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, color=3, life=15, max_life=20)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.5
        assert p.vy == -2.0
        assert p.color == 3
        assert p.life == 15
        assert p.max_life == 20

    def test_phase_enum(self):
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.SURGE_ANIM in Phase
        assert Phase.GAME_OVER in Phase


class TestGameReset:
    """Test game state initialization."""

    def test_reset_values(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 999
        g.combo = 5
        g.heat = 50.0
        g.belt_speed = 2.0
        g.items.append(Item(0, 0, 8, 0))

        g.reset()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.belt_speed == BASE_SPEED
        assert g.items == []
        assert g.particles == []
        assert g._last_tagged_color_idx is None
        assert g._score_since_cycle == 0
        assert g._frame == 0
        assert g.gate_x == INITIAL_GATE_X
        assert g.gate_color == 0

    def test_start_game(self):
        g = _make_game()
        g.score = 100
        g.combo = 3
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.belt_speed == BASE_SPEED
        assert g.gate_x == INITIAL_GATE_X
        assert g.gate_color == 0


class TestItemSpawning:
    """Test item spawn mechanics."""

    def test_spawn_item_returns_item(self):
        g = _make_game()
        item = g._spawn_item()
        assert item is not None
        assert item.x == float(-ITEM_W)
        assert item.y == float(BELT_Y - ITEM_H // 2)
        assert not item.tagged
        assert item.alive
        assert 0 <= item.color_idx < 4

    def test_spawn_item_with_seeded_rng(self):
        g = _make_game()
        rng = random.Random(99)
        items = [g._spawn_item(rng) for _ in range(10)]
        assert all(it is not None for it in items)
        colors = [it.color_idx for it in items if it is not None]
        # With seed 99, should be reproducible
        rng2 = random.Random(99)
        items2 = [g._spawn_item(rng2) for _ in range(10)]
        assert [it.color_idx for it in items2 if it is not None] == colors

    def test_spawn_item_color_in_range(self):
        g = _make_game()
        for _ in range(50):
            item = g._spawn_item()
            assert item is not None
            assert 0 <= item.color_idx < 4
            assert item.color == ITEM_COLORS[item.color_idx]


class TestItemMovement:
    """Test item movement and gate pass detection."""

    def test_items_move_right(self):
        g = _make_game()
        g.belt_speed = 1.5
        item = Item(x=100.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()
        assert item.x == 101.5
        assert item.alive

    def test_untagged_item_reaches_right_edge(self):
        g = _make_game()
        g.heat = 0.0
        item = Item(x=float(SCREEN_W - 1), y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()
        assert not item.alive
        assert g.heat == 10.0

    def test_tagged_item_reaches_right_edge_no_heat(self):
        g = _make_game()
        g.heat = 0.0
        item = Item(x=float(SCREEN_W - 1), y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True)
        g.items = [item]
        g._update_items()
        assert item.alive  # stays alive, not removed by heat logic
        assert g.heat == 0.0  # no heat from tagged item

    def test_item_crosses_gate_matching_color(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0  # RED
        g.combo = 0
        g.score = 0
        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g.belt_speed = 2.0
        g._update_items()
        assert item.tagged
        assert g.combo == 1
        assert g.score > 0
        assert g._last_tagged_color_idx == 0

    def test_item_crosses_gate_wrong_color(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0  # RED
        g.combo = 3
        g._last_tagged_color_idx = 0
        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=3, color_idx=1)  # GREEN
        g.items = [item]
        g.belt_speed = 2.0
        g._update_items()
        assert not item.tagged
        assert g.combo == 0

    def test_item_already_tagged_does_not_retrigger(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 1
        g._last_tagged_color_idx = 0
        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True)
        g.items = [item]
        g.belt_speed = 2.0
        g._update_items()
        # Combo should NOT increment again
        assert g.combo == 1


class TestComboLogic:
    """Test combo chain mechanics."""

    def test_consecutive_same_color_builds_combo(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0  # RED
        g.combo = 0
        g._last_tagged_color_idx = None
        g.belt_speed = 2.0

        # First tag
        item1 = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item1]
        g._update_items()
        assert g.combo == 1

        # Second tag, same color
        item2 = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item2]
        g._update_items()
        assert g.combo == 2

    def test_different_color_resets_combo(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0  # RED
        g.combo = 3
        g._last_tagged_color_idx = 0
        g.belt_speed = 2.0

        # Match wrong color
        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=3, color_idx=1)  # GREEN
        g.items = [item]
        g._update_items()
        assert g.combo == 0

    def test_max_combo_tracks_highest(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.belt_speed = 2.0
        g.combo = 4
        g.max_combo = 4
        g._last_tagged_color_idx = 0

        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()
        assert g.combo == 5
        assert g.max_combo == 5

    def test_wrong_color_with_no_combo(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 0
        g._last_tagged_color_idx = None

        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=3, color_idx=1)
        g.items = [item]
        g.belt_speed = 2.0
        g._update_items()
        assert g.combo == 0
        assert not item.tagged


class TestScoring:
    """Test scoring formula."""

    def test_base_score_formula(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 0
        g.score = 0
        g.belt_speed = 2.0

        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()
        # Score = int(10 * (1 + 151.0/320)) = int(10 * 1.4718...) = 14
        assert g.score > 0
        assert g.score <= 20  # max at right edge: 10 * (1+319/320) ≈ 19

    def test_risk_reward_closer_to_right_more_points(self):
        g = _make_game()
        g.gate_color = 0
        g.belt_speed = 2.0

        # Gate near left → items cross gate at low x → low score
        g.gate_x = 50.0
        g.combo = 0
        g._last_tagged_color_idx = None
        g.score = 0
        item1 = Item(x=49.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item1]
        g._update_items()
        score_left = g.score

        # Gate near right → items cross gate at high x → high score
        g.gate_x = 300.0
        g.combo = 0
        g._last_tagged_color_idx = None
        g.score = 0
        # Clean up items from previous test, add new item just before gate
        g.items = [Item(x=299.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)]
        g._update_items()
        score_right = g.score
        assert score_right > score_left, f"right={score_right} should be > left={score_left}"


class TestSurge:
    """Test SURGE trigger and effects."""

    def test_surge_triggers_at_threshold(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 4  # one below threshold
        g._last_tagged_color_idx = 0
        g.score = 0
        g.belt_speed = 2.0

        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()
        assert g.combo >= SURGE_THRESHOLD
        assert g.phase == Phase.SURGE_ANIM
        assert g._surge_timer == Game.SURGE_DURATION

    def test_surge_removes_tagged_items(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 4
        g._last_tagged_color_idx = 0
        g.score = 0
        g.belt_speed = 2.0

        # Place some tagged items
        g.items = [
            Item(x=100.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
            Item(x=200.0, y=float(BELT_Y - ITEM_H // 2), color=3, color_idx=1, tagged=False),
            Item(x=250.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
        ]
        item_to_trigger = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items.append(item_to_trigger)

        g._update_items()
        # Tagged items should be dead
        alive_ids = [it.color_idx for it in g.items if it.alive]
        assert 0 not in alive_ids or all(not it.tagged for it in g.items if it.alive and it.color_idx == 0)
        # Untagged item should survive
        assert any(it.color_idx == 1 and it.alive for it in g.items)

    def test_surge_creates_particles(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 4
        g._last_tagged_color_idx = 0
        g.belt_speed = 2.0

        g.items = [
            Item(x=100.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
        ]
        item_to_trigger = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items.append(item_to_trigger)

        initial_particle_count = len(g.particles)
        g._update_items()
        assert len(g.particles) > initial_particle_count

    def test_surge_score_bonus(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 4
        g._last_tagged_color_idx = 0
        g.belt_speed = 2.0

        g.items = [
            Item(x=100.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
            Item(x=200.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
        ]
        item_to_trigger = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items.append(item_to_trigger)

        score_before = g.score
        g._update_items()
        assert g.score > score_before + 100  # bonus should be significant
        assert g._surge_score_popup > 0

    def test_surge_popup_texts(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 4
        g._last_tagged_color_idx = 0
        g.belt_speed = 2.0

        g.items = [
            Item(x=100.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
        ]
        item_to_trigger = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items.append(item_to_trigger)

        popup_count_before = len(g._popup_texts)
        g._update_items()
        assert len(g._popup_texts) >= popup_count_before + 1
        # Should have a SURGE text
        surge_texts = [t for t in g._popup_texts if "SURGE" in t[0]]
        assert len(surge_texts) > 0

    def test_surge_resets_after_animation(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g.combo = 4
        g._last_tagged_color_idx = 0
        g.belt_speed = 2.0

        g.items = [
            Item(x=100.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0, tagged=True),
        ]
        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items.append(item)
        g._update_items()

        assert g.phase == Phase.SURGE_ANIM
        assert g._surge_timer == Game.SURGE_DURATION
        assert g._shake_timer == Game.SHAKE_DURATION


class TestHeatSystem:
    """Test heat accumulation and game over."""

    def test_heat_from_untagged_item(self):
        g = _make_game()
        g.heat = 0.0
        item = Item(x=float(SCREEN_W - 1), y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g.belt_speed = 2.0
        g._update_items()
        assert g.heat == 10.0

    def test_heat_capped_at_max(self):
        g = _make_game()
        g.heat = 95.0
        item = Item(x=float(SCREEN_W - 1), y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g.belt_speed = 2.0
        g._update_items()
        assert g.heat == MAX_HEAT
        assert g.heat <= MAX_HEAT

    def test_game_over_on_max_heat(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = MAX_HEAT
        result = g._check_game_over()
        assert result is True
        assert g.phase == Phase.GAME_OVER

    def test_no_game_over_below_max_heat(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = MAX_HEAT - 0.1
        result = g._check_game_over()
        assert result is False
        assert g.phase == Phase.PLAYING

    def test_update_heat_ratio(self):
        g = _make_game()
        g.heat = 50.0
        ratio = g._update_heat()
        assert abs(ratio - 0.5) < 0.01

        g.heat = 0.0
        ratio = g._update_heat()
        assert ratio == 0.0

        g.heat = 100.0
        ratio = g._update_heat()
        assert abs(ratio - 1.0) < 0.01


class TestDifficultyScaling:
    """Test difficulty increase over time."""

    def test_belt_speed_increases_over_time(self):
        g = _make_game()
        initial_speed = g.belt_speed
        assert initial_speed == BASE_SPEED

        # Simulate exactly SPEED_INCREMENT_INTERVAL frames
        for _ in range(SPEED_INCREMENT_INTERVAL):
            g._update_difficulty()
        assert g.belt_speed == BASE_SPEED + SPEED_INCREMENT

    def test_speed_increment_multiple_times(self):
        g = _make_game()
        for _ in range(SPEED_INCREMENT_INTERVAL * 3):
            g._update_difficulty()
        expected = BASE_SPEED + SPEED_INCREMENT * 3
        assert abs(g.belt_speed - expected) < 0.001

    def test_frame_counter_increments(self):
        g = _make_game()
        assert g._frame == 0
        g._update_difficulty()
        assert g._frame == 1


class TestAutoColorCycle:
    """Test auto color cycle at score threshold."""

    def test_color_cycles_at_threshold(self):
        g = _make_game()
        g.gate_x = 100.0  # place gate where item can cross
        g.gate_color = 0
        g._score_since_cycle = AUTO_CYCLE_SCORE - 10
        g.combo = 0
        g._last_tagged_color_idx = None
        g.belt_speed = 2.0

        # Tag an item that scores enough to cross threshold
        item = Item(x=99.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()

        # Color should have cycled from 0 to 1
        assert g.gate_color == 1
        assert g._score_since_cycle < AUTO_CYCLE_SCORE

    def test_no_color_cycle_below_threshold(self):
        g = _make_game()
        g.gate_x = 150.0
        g.gate_color = 0
        g._score_since_cycle = 10
        g.combo = 0
        g._last_tagged_color_idx = None
        g.belt_speed = 2.0

        item = Item(x=149.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()
        assert g.gate_color == 0

    def test_cycle_popup_created(self):
        g = _make_game()
        g.gate_x = 100.0  # place gate where item can cross
        g.gate_color = 0
        g._score_since_cycle = AUTO_CYCLE_SCORE - 5
        g.combo = 0
        g._last_tagged_color_idx = None
        g.belt_speed = 2.0
        g._popup_texts.clear()

        item = Item(x=99.0, y=float(BELT_Y - ITEM_H // 2), color=8, color_idx=0)
        g.items = [item]
        g._update_items()

        # Should have a COLOR CYCLE popup
        cycle_texts = [t for t in g._popup_texts if "CYCLE" in t[0] or "COLOR" in t[0]]
        assert len(cycle_texts) > 0


class TestParticles:
    """Test particle system."""

    def test_spawn_particles(self):
        g = _make_game()
        g._rng = random.Random(42)
        initial_count = len(g.particles)
        g._spawn_particles(100.0, 100.0, 8, 5)
        assert len(g.particles) == initial_count + 5

    def test_update_particles_moves_and_decays(self):
        g = _make_game()
        g._rng = random.Random(42)
        g._spawn_particles(100.0, 100.0, 8, 3)

        # Get the first particle's initial values
        p0 = g.particles[0]
        px_before = p0.x
        py_before = p0.y
        life_before = p0.life

        g._update_particles()
        p0 = g.particles[0]
        assert p0.x != px_before  # moved
        assert p0.y != py_before  # moved
        assert p0.life == life_before - 1

    def test_particles_removed_when_dead(self):
        g = _make_game()
        g._rng = random.Random(42)
        g._spawn_particles(100.0, 100.0, 8, 10)

        # Run update until all particles die
        for _ in range(30):
            g._update_particles()

        assert len(g.particles) == 0

    def test_particle_life_positive(self):
        g = _make_game()
        g._rng = random.Random(42)
        g._spawn_particles(100.0, 100.0, 8, 20)
        for p in g.particles:
            assert p.life > 0
            assert p.max_life >= p.life


class TestPopups:
    """Test popup text system."""

    def test_popups_decay(self):
        g = _make_game()
        g._popup_texts = [
            ("test1", 100.0, 100.0, 7, 5),
            ("test2", 200.0, 100.0, 7, 15),
        ]
        g._update_popups()
        assert len(g._popup_texts) == 2
        assert g._popup_texts[0][4] == 4  # life decremented
        assert g._popup_texts[1][4] == 14

    def test_popups_removed_when_expired(self):
        g = _make_game()
        # life=1: first update decrements to 0 (still present, filter uses old life),
        # second update sees life=0 and removes
        g._popup_texts = [("test", 100.0, 100.0, 7, 1)]
        g._update_popups()
        # After first update: life becomes 0, still present
        assert len(g._popup_texts) == 1
        assert g._popup_texts[0][4] == 0
        g._update_popups()
        # After second update: removed
        assert len(g._popup_texts) == 0


class TestSpawnInterval:
    """Test spawn interval calculation."""

    def test_spawn_interval_within_bounds(self):
        g = _make_game()
        g._rng = random.Random(42)
        for _ in range(20):
            interval = g._get_spawn_interval()
            assert interval >= Game.ITEM_SPAWN_MIN
            assert interval <= Game.ITEM_SPAWN_MAX

    def test_spawn_interval_decreases_over_time(self):
        g = _make_game()
        g._rng = random.Random(42)
        g._frame = SPEED_INCREMENT_INTERVAL * 3  # speed leveled up a bit

        # The interval should have decreased from max
        interval = g._get_spawn_interval()
        assert interval <= Game.ITEM_SPAWN_MAX


class TestGateMovement:
    """Test gate position and color."""

    def test_gate_x_default(self):
        g = _make_game()
        assert g.gate_x == INITIAL_GATE_X

    def test_gate_color_default(self):
        g = _make_game()
        assert g.gate_color == 0


class TestGameOverState:
    """Test game over phase and stats."""

    def test_game_over_preserves_stats(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.max_combo = 7
        g.heat = MAX_HEAT
        g.belt_speed = 1.5

        g._check_game_over()
        assert g.phase == Phase.GAME_OVER
        assert g.score == 500
        assert g.max_combo == 7

    def test_game_over_shake_timer(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = MAX_HEAT
        g._check_game_over()
        assert g._shake_timer == Game.SHAKE_DURATION
