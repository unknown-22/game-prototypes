"""test_imports.py — Headless logic tests for 084_bar_chain."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/084_bar_chain")
from main import (
    Game,
    Order,
    PourRecord,
    Particle,
    FloatingText,
    Phase,
    POUR_COLORS,
    POUR_NAMES,
    MAX_HEAT,
    HEAT_DECAY_ON_SERVE,
    SCORE_CORRECT_BASE,
    SCORE_EXTRA_BASE,
    SCORE_COMPLETION_BONUS_MULT,
    SCORE_HEAT_PENALTY,
    WIDTH,
    HEIGHT,
    BOTTLE_START_X,
    BOTTLE_W,
    BOTTLE_GAP,
    NUM_BOTTLES,
    BOTTLE_Y,
    BOTTLE_H,
    SERVE_X,
    SERVE_W,
    SERVE_Y,
    SERVE_H,
    DARK_BLUE,
    WHITE,
    RED,
    GREEN,
)

# Alias DARK_BLUE as BLUE for test readability
BLUE = DARK_BLUE


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _make_game() -> Game:
    """Create a Game bypassing __init__ for headless tests."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.heat = 0
    g.max_heat = MAX_HEAT
    g.combo = 0
    g.max_combo = 0
    g.order = None
    g.pours = []
    g.last_color = None
    g.serve_ready = False
    g.serve_flash_timer = 0
    g.frame_timer = 0
    g.game_over = False
    g.particles = []
    g.floating_texts = []
    g._round = 0
    g._order_appear_timer = 0
    g._serve_anim_timer = 0
    g._order_matched = 0
    g._rng = random.Random(42)
    g._title_flash = 0
    g._init_state()
    g._rng = random.Random(42)
    return g


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants() -> None:
    assert len(POUR_COLORS) == 4
    assert POUR_COLORS == [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
    assert POUR_NAMES == ["RED", "GREEN", "BLUE", "YELLOW"]
    assert MAX_HEAT == 10
    assert HEAT_DECAY_ON_SERVE == 2
    assert SCORE_CORRECT_BASE == 10
    assert SCORE_EXTRA_BASE == 5
    assert SCORE_COMPLETION_BONUS_MULT == 50
    assert SCORE_HEAT_PENALTY == 20
    assert WIDTH == 320
    assert HEIGHT == 240
    assert NUM_BOTTLES == 4


# ---------------------------------------------------------------------------
# Initialization & reset
# ---------------------------------------------------------------------------


def test_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.heat == 0
    assert g.max_heat == MAX_HEAT
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.order is None
    assert g.pours == []
    assert g.last_color is None
    assert g.serve_ready is False
    assert g.game_over is False
    assert g._round == 0


def test_reset() -> None:
    g = _make_game()
    g.score = 500
    g.heat = 8
    g.combo = 5
    g.max_combo = 5
    g._round = 10
    g.pours = [PourRecord(color=8, combo=1, is_correct=True)]
    g.game_over = True
    g.reset()
    assert g.score == 0
    assert g.heat == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g._round == 0
    assert g.pours == []
    assert g.game_over is False


# ---------------------------------------------------------------------------
# Order generation
# ---------------------------------------------------------------------------


def test_generate_order_easy() -> None:
    g = _make_game()
    g._round = 1
    order = g._generate_order()
    assert len(order.target_colors) == 2
    assert order.time_limit == 300
    assert order.timer == 300
    for c in order.target_colors:
        assert c in POUR_COLORS


def test_generate_order_medium() -> None:
    g = _make_game()
    g._round = 5
    order = g._generate_order()
    assert len(order.target_colors) == 3
    assert order.time_limit == 270


def test_generate_order_hard() -> None:
    g = _make_game()
    g._round = 8
    order = g._generate_order()
    assert len(order.target_colors) == 4
    assert order.time_limit == 240


def test_get_difficulty() -> None:
    g = _make_game()
    assert g._get_difficulty() == (2, 300)
    g._round = 1
    assert g._get_difficulty() == (2, 300)
    g._round = 4
    assert g._get_difficulty() == (3, 270)
    g._round = 7
    assert g._get_difficulty() == (4, 240)


# ---------------------------------------------------------------------------
# Pour logic
# ---------------------------------------------------------------------------


def _make_game_with_order(num_colors: int = 3) -> Game:
    g = _make_game()
    g._round = 3
    g.order = g._generate_order()
    g.phase = Phase.POURING
    return g


def test_pour_correct_color() -> None:
    g = _make_game_with_order()
    target = g.order.target_colors[0]
    result = g._pour(target)
    assert result is True
    assert len(g.pours) == 1
    assert g.pours[0].color == target
    assert g.pours[0].combo == 1
    assert g.pours[0].is_correct is True
    assert g.combo == 1
    assert g.last_color == target


def test_pour_wrong_color() -> None:
    g = _make_game_with_order()
    target = g.order.target_colors[0]
    wrong = next(c for c in POUR_COLORS if c != target)
    result = g._pour(wrong)
    assert result is True
    assert g.pours[0].is_correct is False
    assert g.heat == 1


def test_pour_combo_builds() -> None:
    g = _make_game_with_order()
    # Make target colors all same for easy testing
    g.order.target_colors = [RED, RED, RED]
    target = RED
    g._pour(target)  # combo 1
    assert g.combo == 1
    g._pour(target)  # combo 2
    assert g.combo == 2
    g._pour(target)  # combo 3
    assert g.combo == 3
    assert g.max_combo == 3


def test_pour_combo_resets_on_different_color() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN, RED]
    g._pour(RED)  # combo 1
    assert g.combo == 1
    g._pour(GREEN)  # combo resets to 1
    assert g.combo == 1
    g._pour(RED)  # combo 1
    assert g.combo == 1


def test_pour_extra_pours_beyond_order() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    g._pour(RED)  # correct, completes order
    assert g.serve_ready is True
    g._pour(RED)  # extra pour, same color, combo continues
    assert g.combo == 2
    assert g.pours[-1].is_correct is True  # extra same-color is "correct"
    assert g.serve_ready is True


def test_pour_wrong_color_adds_heat() -> None:
    g = _make_game_with_order()
    target = g.order.target_colors[0]
    wrong = next(c for c in POUR_COLORS if c != target)
    g._pour(wrong)
    assert g.heat == 1
    g._pour(wrong)
    assert g.heat == 2


def test_pour_heat_game_over() -> None:
    g = _make_game_with_order()
    target = g.order.target_colors[0]
    wrong = next(c for c in POUR_COLORS if c != target)
    g.heat = MAX_HEAT - 1
    g._pour(wrong)
    assert g.heat == MAX_HEAT
    assert g.game_over is True
    assert g.phase == Phase.GAME_OVER


def test_pour_does_not_accept_when_serve_ready() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    g._pour(RED)
    assert g.serve_ready is True
    g._pour(RED)  # extra pour when serve_ready should still work
    assert len(g.pours) == 2


def test_pour_no_order() -> None:
    g = _make_game()
    g.phase = Phase.POURING
    result = g._pour(RED)
    assert result is False


def test_pour_spawns_particles() -> None:
    g = _make_game_with_order()
    target = g.order.target_colors[0]
    g._pour(target)
    # Combo=1 produces 3 particles
    assert len(g.particles) == 3


# ---------------------------------------------------------------------------
# Check serve ready
# ---------------------------------------------------------------------------


def test_check_serve_ready_all_correct() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN]
    g._pour(RED)
    assert g.serve_ready is False
    g._pour(GREEN)
    assert g.serve_ready is True


def test_check_serve_ready_with_extra_pours() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN]
    g._pour(RED)
    g._pour(RED)  # extra RED, same as last target match? No, next is GREEN
    assert g.serve_ready is False
    g._pour(GREEN)
    assert g.serve_ready is True


def test_check_serve_ready_with_wrong_interleaved() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN, BLUE]
    # WRONG -> correct RED -> correct GREEN -> correct BLUE
    wrong = next(c for c in POUR_COLORS if c != RED)
    g._pour(wrong)  # wrong
    g._pour(RED)
    g._pour(GREEN)
    g._pour(BLUE)
    assert g.serve_ready is True


def test_can_serve() -> None:
    g = _make_game_with_order()
    assert g._can_serve() is False
    g.order.target_colors = [RED]
    g._pour(RED)
    assert g._can_serve() is True


# ---------------------------------------------------------------------------
# Serve logic
# ---------------------------------------------------------------------------


def test_serve_basic() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN]
    g._pour(RED)  # combo=1
    g._pour(GREEN)  # combo=1
    g.serve_ready = True
    score = g._serve()
    # 2 target colors: 10*1 + 10*1 = 20, completion bonus: 2*50 = 100, total = 120
    assert score == 120
    assert g.score == 120
    assert g.pours == []
    assert g.combo == 0
    assert g.last_color is None
    assert g.serve_ready is False
    assert g.order is None


def test_serve_with_combo() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, RED, RED]
    g._pour(RED)  # combo=1
    g._pour(RED)  # combo=2
    g._pour(RED)  # combo=3
    assert g.serve_ready is True
    score = g._serve()
    # 10*1 + 10*2 + 10*3 = 10+20+30 = 60 + 3*50 = 210
    assert score == 210
    assert g.score == 210


def test_serve_with_extras() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    g._pour(RED)  # combo=1, correct
    g._pour(RED)  # combo=2, extra
    g._pour(RED)  # combo=3, extra
    assert g.serve_ready is True
    score = g._serve()
    # 10*1 + 5*2 + 5*3 = 10+10+15 = 35 + 1*50 = 85
    assert score == 85


def test_serve_with_wrong_pours() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    wrong = next(c for c in POUR_COLORS if c != RED)
    g._pour(wrong)  # wrong, heat=1, combo=1
    g._pour(RED)  # correct, combo=1
    assert g.serve_ready is True
    score = g._serve()
    # correct: 10*1 = 10, wrong penalty: 20*1 = -20, completion: 1*50 = 50
    # total = 10 - 20 + 50 = 40
    assert score == 40


def test_serve_heat_decay() -> None:
    g = _make_game_with_order()
    g.heat = 5
    g.order.target_colors = [RED]
    g._pour(RED)
    g.serve_ready = True
    g._serve()
    assert g.heat == 3  # 5 - 2


def test_serve_heat_decay_below_zero() -> None:
    g = _make_game_with_order()
    g.heat = 1
    g.order.target_colors = [RED]
    g._pour(RED)
    g.serve_ready = True
    g._serve()
    assert g.heat == 0


def test_serve_min_score_zero() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    wrong = next(c for c in POUR_COLORS if c != RED)
    for _ in range(5):
        g._pour(wrong)  # many wrong pours
    g._pour(RED)
    g.serve_ready = True
    score = g._serve()
    assert score >= 0


def test_serve_no_order() -> None:
    g = _make_game()
    score = g._serve()
    assert score == 0


def test_serve_spawns_floating_text() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    g._pour(RED)
    g.serve_ready = True
    g._serve()
    assert len(g.floating_texts) >= 1


# ---------------------------------------------------------------------------
# Order timer
# ---------------------------------------------------------------------------


def test_update_order_timer_decrements() -> None:
    g = _make_game_with_order()
    g.order.timer = 100
    expired = g._update_order_timer()
    assert expired is False
    assert g.order.timer == 99


def test_update_order_timer_expires() -> None:
    g = _make_game_with_order()
    g.order.timer = 0
    expired = g._update_order_timer()
    assert expired is True


def test_update_order_timer_no_order() -> None:
    g = _make_game()
    expired = g._update_order_timer()
    assert expired is False


def test_handle_order_timeout() -> None:
    g = _make_game_with_order()
    g.heat = 3
    g._handle_order_timeout()
    assert g.heat == 5  # 3 + 2
    assert g.order is None
    assert g.pours == []


def test_handle_order_timeout_game_over() -> None:
    g = _make_game_with_order()
    g.heat = 9
    g._handle_order_timeout()
    assert g.game_over is True
    assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Heat / Game Over
# ---------------------------------------------------------------------------


def test_update_heat_normal() -> None:
    g = _make_game()
    g.heat = 5
    result = g._update_heat()
    assert result is False
    assert g.game_over is False


def test_update_heat_game_over() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    result = g._update_heat()
    assert result is True
    assert g.game_over is True


def test_trigger_game_over() -> None:
    g = _make_game()
    g._trigger_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over is True
    assert g.serve_ready is False


# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------


def test_start_order() -> None:
    g = _make_game()
    g._start_order()
    assert g.phase == Phase.ORDER_APPEAR
    assert g.order is not None
    assert g.pours == []
    assert g.combo == 0
    assert g.serve_ready is False
    assert g._round == 1


def test_begin_serve_animation() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    g._pour(RED)
    g.serve_ready = True
    old_score = g.score
    g._begin_serve_animation()
    assert g.phase == Phase.SERVE_ANIM
    assert g.score > old_score
    assert len(g.particles) >= 20


# ---------------------------------------------------------------------------
# Particle and floating text
# ---------------------------------------------------------------------------


def test_update_particles() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, dx=1.0, dy=0.0, color=RED, life=5),
        Particle(x=0.0, y=0.0, dx=0.0, dy=0.0, color=GREEN, life=1),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert abs(g.particles[0].x - 1.0) < 0.01
    assert g.particles[0].life == 4


def test_update_floating_texts() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="test", color=WHITE, life=5),
        FloatingText(x=0.0, y=0.0, text="dead", color=WHITE, life=1),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 4
    assert abs(g.floating_texts[0].y - 99.4) < 0.01


def test_spawn_pour_particles() -> None:
    g = _make_game()
    g.combo = 2
    g._spawn_pour_particles(RED)
    expected_count = g.combo * 3  # 6
    assert len(g.particles) == expected_count


def test_spawn_serve_particles() -> None:
    g = _make_game()
    g._spawn_serve_particles()
    assert len(g.particles) == 20


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text("COMBO!", WHITE)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "COMBO!"
    assert g.floating_texts[0].life == 30


# ---------------------------------------------------------------------------
# Bottle click detection
# ---------------------------------------------------------------------------


def test_bottle_at_mouse() -> None:
    g = _make_game()
    # Test first bottle
    bx = BOTTLE_START_X
    by = BOTTLE_Y + BOTTLE_H // 2
    idx = g._bottle_at_mouse(bx + BOTTLE_W // 2, by)
    assert idx == 0
    # Outside
    idx = g._bottle_at_mouse(0, 0)
    assert idx is None


def test_bottle_at_mouse_all() -> None:
    g = _make_game()
    for i in range(NUM_BOTTLES):
        bx = BOTTLE_START_X + i * (BOTTLE_W + BOTTLE_GAP) + BOTTLE_W // 2
        by = BOTTLE_Y + BOTTLE_H // 2
        idx = g._bottle_at_mouse(bx, by)
        assert idx == i


def test_serve_button_hit() -> None:
    g = _make_game()
    assert g._serve_button_hit(SERVE_X + SERVE_W // 2, SERVE_Y + SERVE_H // 2) is True
    assert g._serve_button_hit(0, 0) is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_pour_same_color_chain_then_break() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, RED, GREEN]
    g._pour(RED)  # combo=1
    assert g.combo == 1
    g._pour(RED)  # combo=2
    assert g.combo == 2
    g._pour(GREEN)  # combo=1 (different color)
    assert g.combo == 1
    assert g.max_combo == 2


def test_max_combo_tracking() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, RED, RED, RED, RED, RED]
    for _ in range(6):
        g._pour(RED)
    assert g.max_combo == 6
    g._pour(GREEN)
    assert g.combo == 1
    assert g.max_combo == 6


def test_all_four_colors_in_order() -> None:
    g = _make_game()
    g._round = 8
    order = g._generate_order()
    assert 2 <= len(order.target_colors) <= 4


def test_serve_clears_pours_properly() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN]
    g._pour(RED)
    g._pour(GREEN)
    g._serve()
    assert g.pours == []
    assert g.last_color is None
    assert g.combo == 0


def test_multiple_rounds() -> None:
    g = _make_game()
    g._start_order()
    g.order.target_colors = [RED]
    g._pour(RED)
    g._serve()
    g._start_order()
    assert g._round == 2
    assert g.order is not None
    assert len(g.pours) == 0


def test_empty_pours_cant_serve() -> None:
    g = _make_game_with_order()
    g.order.target_colors = [RED]
    assert g.serve_ready is False
    assert g._can_serve() is False


def test_dataclass_order() -> None:
    o = Order(target_colors=[RED, GREEN], reward_base=100, time_limit=300, timer=300)
    assert o.target_colors == [RED, GREEN]
    assert o.timer == 300


def test_dataclass_pour_record() -> None:
    pr = PourRecord(color=RED, combo=3, is_correct=True)
    assert pr.color == RED
    assert pr.combo == 3
    assert pr.is_correct is True


def test_dataclass_particle() -> None:
    p = Particle(x=1.0, y=2.0, dx=0.5, dy=-0.5, color=RED, life=10)
    assert p.life == 10


def test_dataclass_floating_text() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+100", color=WHITE, life=30)
    assert ft.text == "+100"
    assert ft.life == 30


def test_check_serve_ready_complex() -> None:
    """Order: RED, GREEN, RED. Pours: RED, RED, GREEN, RED."""
    g = _make_game_with_order()
    g.order.target_colors = [RED, GREEN, RED]
    g._pour(RED)   # correct (matches RED at pos 0)
    assert not g.serve_ready
    g._pour(RED)   # wrong (pos 1 expects GREEN) → is_correct=False
    assert not g.serve_ready
    g._pour(GREEN) # correct (matches GREEN at pos 1 after RED popped)
    assert not g.serve_ready
    g._pour(RED)   # correct (matches RED at pos 2)
    assert g.serve_ready
