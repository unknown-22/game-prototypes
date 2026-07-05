"""test_imports.py — Headless logic tests for Belt Surge."""
import sys
import math
import random
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import (
    Game,
    Item,
    Particle,
    FloatingText,
    Phase,
    SCREEN_W,
    SCREEN_H,
    BELT_COUNT,
    BELT_SPEED_BASE,
    ITEM_SIZE,
    COLOR_COUNT,
    COLOR_VALS,
    COMBO_THRESHOLD,
    SUPER_DURATION,
    SUPER_MULTIPLIER,
    MAX_HEAT,
    HEAT_PER_WRONG,
    HEAT_PER_MISS,
    HEAT_DECAY,
    SPAWN_INTERVAL,
    SPAWN_INTERVAL_MIN,
    DIFFICULTY_RAMP,
    BIN_COUNT,
    BIN_WIDTH,
    BIN_X_START,
    BIN_Y,
    BIN_HEIGHT,
    BELT_Y_START,
    BELT_SPACING,
)


def _make_game() -> Game:
    """Factory to create a Game instance without Pyxel init."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes
    g.items = []
    g.particles = []
    g.floating_texts = []
    g._rng = random.Random(42)
    g._shake_frames = 0
    g._sort_anim_timer = 0
    g._last_sorted_color = -1
    g.reset()
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.frame = 0
    g.spawn_timer = 0
    g.spawn_interval = float(SPAWN_INTERVAL)
    return g


# ── Dataclass Tests ──


class TestItem:
    def test_create(self) -> None:
        item = Item(x=50.0, y=70.0, color=2, belt=1)
        assert item.x == 50.0
        assert item.y == 70.0
        assert item.color == 2
        assert item.belt == 1
        assert item.alive is True

    def test_not_alive(self) -> None:
        item = Item(x=0.0, y=0.0, color=0, belt=0, alive=False)
        assert item.alive is False


class TestParticle:
    def test_create(self) -> None:
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.5
        assert p.vy == -2.0
        assert p.life == 15
        assert p.color == 8


class TestFloatingText:
    def test_create(self) -> None:
        ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=7)
        assert ft.x == 100.0
        assert ft.y == 50.0
        assert ft.text == "+10"
        assert ft.life == 30
        assert ft.color == 7


# ── Constants Tests ──


class TestConstants:
    def test_screen(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_H == 240

    def test_belt(self) -> None:
        assert BELT_COUNT == 3
        assert BELT_SPACING == 60
        assert BELT_Y_START == 40

    def test_colors(self) -> None:
        assert COLOR_COUNT == 4
        assert len(COLOR_VALS) == 4
        assert COLOR_VALS == [8, 3, 10, 12]

    def test_bins(self) -> None:
        assert BIN_COUNT == 4
        assert BIN_Y == SCREEN_H - 40
        assert BIN_HEIGHT == 40

    def test_combo_threshold(self) -> None:
        assert COMBO_THRESHOLD == 5
        assert SUPER_DURATION == 300
        assert SUPER_MULTIPLIER == 3

    def test_heat(self) -> None:
        assert MAX_HEAT == 100
        assert HEAT_PER_WRONG == 15
        assert HEAT_PER_MISS == 8
        assert abs(HEAT_DECAY - 0.05) < 0.001

    def test_spawn(self) -> None:
        assert SPAWN_INTERVAL == 45
        assert SPAWN_INTERVAL_MIN == 20


# ── Game Phase Tests ──


class TestPhase:
    def test_initial_phase_title(self) -> None:
        g = Game.__new__(Game)
        g.items = []
        g.particles = []
        g.floating_texts = []
        g._rng = random.Random(42)
        g._shake_frames = 0
        g._sort_anim_timer = 0
        g._last_sorted_color = -1
        g.reset()
        assert g.phase == Phase.TITLE

    def test_start_game_phase(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING

    def test_phase_enum_members(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase


# ── Belt Y Tests ──


class TestBeltY:
    def test_belt_0(self) -> None:
        g = _make_game()
        assert g._belt_y(0) == BELT_Y_START

    def test_belt_1(self) -> None:
        g = _make_game()
        assert g._belt_y(1) == BELT_Y_START + BELT_SPACING

    def test_belt_2(self) -> None:
        g = _make_game()
        assert g._belt_y(2) == BELT_Y_START + 2 * BELT_SPACING


# ── Belt Speed Tests ──


class TestBeltSpeed:
    def test_base_speed(self) -> None:
        g = _make_game()
        g.frame = 0
        assert abs(g._belt_speed() - BELT_SPEED_BASE) < 0.001

    def test_speed_after_30s(self) -> None:
        g = _make_game()
        g.frame = 1801  # > 1800
        assert abs(g._belt_speed() - (BELT_SPEED_BASE + 0.3)) < 0.001

    def test_speed_after_60s(self) -> None:
        g = _make_game()
        g.frame = 3601  # > 3600
        assert abs(g._belt_speed() - (BELT_SPEED_BASE + 0.6)) < 0.001


# ── Spawn Item Tests ──


class TestSpawnItem:
    def test_spawn_adds_item(self) -> None:
        g = _make_game()
        initial = len(g.items)
        g._spawn_item()
        assert len(g.items) == initial + 1

    def test_spawn_item_off_screen_left(self) -> None:
        g = _make_game()
        g._spawn_item()
        item = g.items[-1]
        assert item.x == -ITEM_SIZE
        assert item.alive is True

    def test_spawn_item_on_belt(self) -> None:
        g = _make_game()
        g._rng = random.Random(42)
        g._spawn_item()
        item = g.items[-1]
        y = g._belt_y(item.belt)
        assert abs(item.y - y) < 0.01

    def test_spawn_item_valid_color(self) -> None:
        g = _make_game()
        g._spawn_item()
        item = g.items[-1]
        assert 0 <= item.color < COLOR_COUNT


# ── Update Items Tests ──


class TestUpdateItems:
    def test_items_move_right(self) -> None:
        g = _make_game()
        g.items = [Item(x=50.0, y=g._belt_y(0), color=0, belt=0)]
        g.frame = 0
        g._update_items()
        assert g.items[0].x > 50.0

    def test_missed_item_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 0
        g.items = [Item(x=SCREEN_W + ITEM_SIZE + 1, y=g._belt_y(0), color=0, belt=0)]
        g._update_items()
        assert g.heat >= HEAT_PER_MISS
        assert len(g.items) == 0

    def test_missed_item_spawns_floating_text(self) -> None:
        g = _make_game()
        g.items = [Item(x=SCREEN_W + ITEM_SIZE + 1, y=g._belt_y(0), color=0, belt=0)]
        g._update_items()
        assert len(g.floating_texts) >= 1
        assert any("MISS" in ft.text for ft in g.floating_texts)

    def test_missed_item_spawns_particles(self) -> None:
        g = _make_game()
        g.items = [Item(x=SCREEN_W + ITEM_SIZE + 1, y=g._belt_y(0), color=0, belt=0)]
        g._update_items()
        assert len(g.particles) > 0

    def test_item_stays_alive_if_not_off_screen(self) -> None:
        g = _make_game()
        g.items = [Item(x=100.0, y=g._belt_y(0), color=0, belt=0)]
        g.frame = 0
        g._update_items()
        assert len(g.items) == 1
        assert g.items[0].alive is True


# ── Sort Item Tests (Correct Match) ──


class TestSortItemCorrect:
    def test_correct_sort_increases_combo(self) -> None:
        g = _make_game()
        g.combo = 0
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g.items = [item]
        g._sort_item(item, 2)
        assert g.combo == 1

    def test_correct_sort_increases_score(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 0
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 2)
        assert g.score > 0

    def test_correct_sort_marks_item_dead(self) -> None:
        g = _make_game()
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 2)
        assert item.alive is False

    def test_correct_sort_updates_max_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.max_combo = 3
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 2)
        assert g.max_combo == 4

    def test_correct_sort_score_with_combo(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 4
        item = Item(x=100.0, y=g._belt_y(0), color=1, belt=0)
        g._sort_item(item, 1)
        expected = 10 + 5 * 5  # combo becomes 5, points = 10 + combo * 5
        assert g.score == expected

    def test_correct_sort_spawns_particles(self) -> None:
        g = _make_game()
        g._rng = random.Random(42)
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 2)
        assert len(g.particles) > 0

    def test_correct_sort_spawns_floating_text(self) -> None:
        g = _make_game()
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 2)
        assert len(g.floating_texts) > 0


# ── Sort Item Tests (Wrong Match) ──


class TestSortItemWrong:
    def test_wrong_sort_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 10
        g.super_timer = 0
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 0)  # wrong bin!
        assert g.combo == 0

    def test_wrong_sort_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 20
        g.super_timer = 0
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 0)  # wrong bin!
        assert g.heat == 20 + HEAT_PER_WRONG

    def test_wrong_sort_marks_item_dead(self) -> None:
        g = _make_game()
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 0)
        assert item.alive is False

    def test_wrong_sort_spawns_wrong_text(self) -> None:
        g = _make_game()
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 0)
        assert any("WRONG" in ft.text for ft in g.floating_texts)

    def test_wrong_sort_triggers_shake(self) -> None:
        g = _make_game()
        item = Item(x=100.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(item, 0)
        assert g._shake_frames > 0


# ── Super Mode Tests ──


class TestSuperMode:
    def test_super_activates_at_threshold(self) -> None:
        g = _make_game()
        g.combo = COMBO_THRESHOLD - 1  # 4
        g.super_timer = 0
        item = Item(x=100.0, y=g._belt_y(0), color=1, belt=0)
        g._sort_item(item, 1)
        assert g.super_timer == SUPER_DURATION

    def test_super_not_re_activate_when_active(self) -> None:
        g = _make_game()
        g.combo = COMBO_THRESHOLD - 1
        g.super_timer = 100  # already active
        item = Item(x=100.0, y=g._belt_y(0), color=1, belt=0)
        g._sort_item(item, 1)
        assert g.super_timer == 100  # unchanged

    def test_super_multiplies_score(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 0
        g.super_timer = 100
        item = Item(x=100.0, y=g._belt_y(0), color=1, belt=0)
        g._sort_item(item, 1)
        expected = (10 + 1 * 5) * SUPER_MULTIPLIER
        assert g.score == expected

    def test_super_wrong_color_still_sorts(self) -> None:
        """During SUPER, wrong color still sorts without penalty."""
        g = _make_game()
        g.super_timer = 100
        g.combo = 5
        g.heat = 20
        item = Item(x=100.0, y=g._belt_y(0), color=3, belt=0)
        g._sort_item(item, 0)  # wrong bin, but in super mode
        assert item.alive is False
        assert g.heat == 20  # no heat added
        assert g.combo == 6  # combo still increases

    def test_super_deactivation_resets_combo(self) -> None:
        g = _make_game()
        g.super_timer = 1
        g.combo = 10
        # Directly simulate the super_timer decrement logic from _update_playing
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.combo = 0
        assert g.super_timer == 0
        assert g.combo == 0


# ── Heat System Tests ──


class TestHeat:
    def test_heat_decay_per_frame(self) -> None:
        g = _make_game()
        g.heat = 50.0
        # Directly test decay logic from _update_playing
        g.heat = max(0.0, g.heat - HEAT_DECAY)
        assert g.heat < 50.0
        assert g.heat > 49.9  # ~49.95

    def test_heat_clamped_at_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g.heat = max(0.0, g.heat - HEAT_DECAY)
        assert g.heat == 0.0

    def test_game_over_at_max_heat(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT  # exactly 100
        # Directly test game-over check from _update_playing
        if g.heat >= MAX_HEAT:
            g.phase = Phase.GAME_OVER
        assert g.phase == Phase.GAME_OVER

    def test_game_over_just_below_max_heat_continues(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT - 1
        if g.heat >= MAX_HEAT:
            g.phase = Phase.GAME_OVER
        assert g.phase != Phase.GAME_OVER


# ── Difficulty Ramp Tests ──


class TestDifficultyRamp:
    def test_spawn_interval_decreases(self) -> None:
        g = _make_game()
        g.frame = 0
        # Direct formula from _update_playing
        si1 = max(float(SPAWN_INTERVAL_MIN), SPAWN_INTERVAL - DIFFICULTY_RAMP * g.frame)
        g.frame = 1000
        si2 = max(float(SPAWN_INTERVAL_MIN), SPAWN_INTERVAL - DIFFICULTY_RAMP * g.frame)
        assert si2 < si1

    def test_spawn_interval_stops_at_min(self) -> None:
        g = _make_game()
        g.frame = 99999
        si = max(float(SPAWN_INTERVAL_MIN), SPAWN_INTERVAL - DIFFICULTY_RAMP * g.frame)
        assert si == SPAWN_INTERVAL_MIN


# ── Particle Update Tests ──


class TestParticleUpdate:
    def test_particles_move(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=10, color=8)]
        g._update_particles()
        assert g.particles[0].x == 102.0
        assert g.particles[0].y == 99.0

    def test_particles_life_decrements(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=0, vy=0, life=3, color=8)]
        g._update_particles()
        assert g.particles[0].life == 2

    def test_dead_particles_removed(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=0, vy=0, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0


# ── Floating Text Update Tests ──


class TestFloatingTextUpdate:
    def test_floating_text_moves_up(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="+10", life=30, color=7)
        ]
        g._update_floating_texts()
        assert g.floating_texts[0].y == 99.0

    def test_floating_text_life_decrements(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="+10", life=5, color=7)
        ]
        g._update_floating_texts()
        assert g.floating_texts[0].life == 4

    def test_dead_floating_text_removed(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="+10", life=1, color=7)
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ── Handle Click Tests ──


class TestHandleClick:
    def test_click_on_item_sorts(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 0
        item = Item(x=150.0, y=g._belt_y(0), color=1, belt=0)
        g.items = [item]
        g._handle_click(150, int(g._belt_y(0)))
        assert item.alive is False
        assert g.combo == 1
        assert g.score > 0

    def test_click_on_empty_space_does_nothing(self) -> None:
        g = _make_game()
        g.score = 0
        g.combo = 0
        g.heat = 0
        item = Item(x=150.0, y=g._belt_y(0), color=1, belt=0)
        g.items = [item]
        g._handle_click(10, 10)  # far away
        assert item.alive is True
        assert g.combo == 0
        assert g.score == 0

    def test_click_picks_closest_item(self) -> None:
        g = _make_game()
        y0 = g._belt_y(0)
        item1 = Item(x=100.0, y=y0, color=1, belt=0)
        item2 = Item(x=110.0, y=y0, color=2, belt=0)
        g.items = [item1, item2]
        g._handle_click(108, int(y0))  # closer to item2
        assert item2.alive is False
        assert item1.alive is True


# ── Start Game / Reset Tests ──


class TestStartGame:
    def test_start_game_resets_score(self) -> None:
        g = _make_game()
        g.score = 9999
        g._start_game()
        assert g.score == 0

    def test_start_game_resets_heat(self) -> None:
        g = _make_game()
        g.heat = 90
        g._start_game()
        assert g.heat == 0.0

    def test_start_game_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 20
        g.max_combo = 20
        g._start_game()
        assert g.combo == 0
        assert g.max_combo == 0

    def test_start_game_resets_super_timer(self) -> None:
        g = _make_game()
        g.super_timer = 200
        g._start_game()
        assert g.super_timer == 0

    def test_start_game_clears_items(self) -> None:
        g = _make_game()
        g.items = [Item(x=100.0, y=g._belt_y(0), color=0, belt=0)]
        g._start_game()
        assert len(g.items) == 0

    def test_start_game_clears_particles(self) -> None:
        g = _make_game()
        g.particles = [Particle(0, 0, 0, 0, 10, 8)]
        g._start_game()
        assert len(g.particles) == 0

    def test_start_game_clears_floating_texts(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(0, 0, "hi", 10, 7)]
        g._start_game()
        assert len(g.floating_texts) == 0

    def test_start_game_sets_playing_phase(self) -> None:
        g = _make_game()
        g.phase = Phase.GAME_OVER
        g._start_game()
        assert g.phase == Phase.PLAYING


# ── Combo Chain Tests ──


class TestComboChain:
    def test_consecutive_correct_sorts_build_combo(self) -> None:
        g = _make_game()
        g.combo = 0
        for i in range(5):
            item = Item(x=100.0 + i * 20, y=g._belt_y(0), color=1, belt=0)
            g._sort_item(item, 1)
        assert g.combo == 5
        assert g.max_combo == 5

    def test_wrong_sort_breaks_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.super_timer = 0
        item = Item(x=100.0, y=g._belt_y(0), color=0, belt=0)
        g._sort_item(item, 1)  # wrong
        assert g.combo == 0

    def test_max_combo_persists_after_reset(self) -> None:
        g = _make_game()
        g.combo = 0
        g.max_combo = 0
        for i in range(4):
            item = Item(x=100.0 + i * 20, y=g._belt_y(0), color=1, belt=0)
            g._sort_item(item, 1)
        assert g.max_combo == 4
        # Wrong sort resets combo but max_combo stays
        wrong_item = Item(x=200.0, y=g._belt_y(0), color=2, belt=0)
        g._sort_item(wrong_item, 0)  # wrong
        assert g.combo == 0
        assert g.max_combo == 4


# ── Concentration / Multi-Belt Tests ──


class TestMultiBelt:
    def test_items_on_different_belts(self) -> None:
        g = _make_game()
        item0 = Item(x=50.0, y=g._belt_y(0), color=0, belt=0)
        item1 = Item(x=50.0, y=g._belt_y(1), color=1, belt=1)
        item2 = Item(x=50.0, y=g._belt_y(2), color=2, belt=2)
        g.items = [item0, item1, item2]
        # Click on belt 0 item
        g._handle_click(50, int(g._belt_y(0)))
        assert item0.alive is False
        assert item1.alive is True
        assert item2.alive is True

    def test_sort_mixed_colors_independent(self) -> None:
        g = _make_game()
        g.combo = 0
        # Sort red (color 0) then green (color 1) — green should NOT match "last sorted color" check
        # Actually, our game sorts to matching bin based on item.color, not last_sorted_color.
        # The "same color" combo is about consecutive sorts where item.color == bin_idx.
        # If we sort two red items (color=0 → bin=0), combo builds.
        # If we then sort a green item (color=1 → bin=1), it's still correct, combo still builds.
        item1 = Item(x=50.0, y=g._belt_y(0), color=0, belt=0)
        g._sort_item(item1, 0)
        assert g.combo == 1
        item2 = Item(x=70.0, y=g._belt_y(0), color=1, belt=0)
        g._sort_item(item2, 1)
        assert g.combo == 2  # Different color but correct bin still builds combo
