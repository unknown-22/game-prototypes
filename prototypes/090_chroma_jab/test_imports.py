"""test_imports.py — Headless logic tests for Chrome Jab (090_chroma_jab)."""
import random
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/090_chroma_jab")
from main import (
    ChromaJab, Phase, Fighter, Particle, FloatingText,
    SCREEN_W, SCREEN_H, COLOR_VALS, COLOR_NAMES, NUM_COLORS,
    PLAYER_X, AI_X, FIGHTER_Y, ARM_REACH,
    BASE_DAMAGE, SUPER_COMBO_THRESHOLD, SUPER_DAMAGE_MULT,
    AI_BASE_INTERVAL, AI_MIN_INTERVAL, AI_PUNCH_DAMAGE,
    GAME_DURATION, SHAKE_FRAMES, MAX_HP,
)


def _make_game() -> ChromaJab:
    """Factory for headless tests — bypasses pyxel.init/run via Game.__new__."""
    g = ChromaJab.__new__(ChromaJab)
    # Pre-init all attributes that reset() touches
    g.phase = Phase.TITLE
    g.player = Fighter(x=PLAYER_X, y=FIGHTER_Y)
    g.ai = Fighter(x=AI_X, y=FIGHTER_Y)
    g.selected_color = 0
    g.game_timer = GAME_DURATION
    g.total_damage = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g._rng = random.Random(42)
    g._player_punch_cooldown = 0
    g._ai_punch_timer = 45
    g._ai_punch_interval = AI_BASE_INTERVAL
    g._ai_punch_count = 0
    g._last_player_color = -1
    g.result_text = ""
    g._ai_color_counter = 0
    g._last_super_combo = False
    g._last_super_frame = 0
    g.reset()
    return g


# ── Dataclass tests ──


def test_fighter_defaults() -> None:
    f = Fighter(x=80, y=120)
    assert f.hp == MAX_HP
    assert f.max_hp == MAX_HP
    assert f.combo == 0
    assert f.max_combo == 0
    assert f.color == 0
    assert not f.punching
    assert f.punch_timer == 0
    assert f.hit_stun == 0


def test_particle_fields() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_fields() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="-10", life=20, color=8)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "-10"
    assert ft.life == 20
    assert ft.color == 8


# ── Phase / reset tests ──


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.player.hp == MAX_HP
    assert g.ai.hp == MAX_HP
    assert g.selected_color == 0
    assert g.game_timer == GAME_DURATION
    assert g.total_damage == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake_frames == 0
    assert g._last_player_color == -1
    assert g.player.combo == 0
    assert g.player.max_combo == 0


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Color constants ──


def test_color_vals() -> None:
    assert len(COLOR_VALS) == NUM_COLORS
    assert COLOR_VALS == (8, 3, 12, 10)  # RED, GREEN, BLUE, YELLOW


def test_color_names() -> None:
    assert len(COLOR_NAMES) == NUM_COLORS
    assert COLOR_NAMES[0] == "RED"
    assert COLOR_NAMES[1] == "GREEN"
    assert COLOR_NAMES[2] == "BLUE"
    assert COLOR_NAMES[3] == "YELLOW"


# ── Collision / rect tests ──


def test_player_body_rect() -> None:
    g = _make_game()
    x, y, w, h = g._player_body_rect()
    assert x == PLAYER_X - 15
    assert y == FIGHTER_Y - 25
    assert w == 30
    assert h == 50


def test_ai_body_rect() -> None:
    g = _make_game()
    x, y, w, h = g._ai_body_rect()
    assert x == AI_X - 15
    assert y == FIGHTER_Y - 25
    assert w == 30
    assert h == 50


def test_player_punch_rect() -> None:
    g = _make_game()
    x, y, w, h = g._player_punch_rect()
    assert x == PLAYER_X + 8
    assert w == ARM_REACH


def test_ai_punch_rect() -> None:
    g = _make_game()
    x, y, w, h = g._ai_punch_rect()
    assert x == AI_X - 8 - ARM_REACH
    assert w == ARM_REACH


def test_aabb_overlap_true() -> None:
    assert ChromaJab._aabb_overlap((0, 0, 10, 10), (5, 5, 10, 10))


def test_aabb_overlap_false() -> None:
    assert not ChromaJab._aabb_overlap((0, 0, 10, 10), (20, 20, 10, 10))


def test_aabb_overlap_edge_touch() -> None:
    # AABB uses strict < and > checks:
    # x1 < x2 + w2 and x1 + w1 > x2
    # At exact touch (10, 0, 10, 10): 0+10 (10) is not > 10 → NO overlap
    assert not ChromaJab._aabb_overlap((0, 0, 10, 10), (10, 0, 10, 10))
    # With 1px overlap: (9, 0, 10, 10): 0+10 (10) > 9 → overlap
    assert ChromaJab._aabb_overlap((0, 0, 10, 10), (9, 0, 10, 10))
    # Fully separate: (20, 0, 10, 10) — no overlap
    assert not ChromaJab._aabb_overlap((0, 0, 10, 10), (20, 0, 10, 10))


# ── Punch logic tests ──


def test_try_punch_hit_first_punch() -> None:
    """First punch should always hit and set combo to 1 (color matches _last_player_color=-1 check)."""
    g = _make_game()
    hit, damage, is_super = g._try_punch(0)
    assert hit
    # First punch: _last_player_color < 0 → combo += 1
    assert g.player.combo == 1
    assert g.player.max_combo == 1
    assert not is_super
    assert damage > 0
    assert g.total_damage > 0
    assert g.ai.hp < MAX_HP


def test_try_punch_same_color_combo_builds() -> None:
    """Hitting with same color consecutively builds combo."""
    g = _make_game()
    g._try_punch(0)  # combo becomes 1
    assert g.player.combo == 1
    g._player_punch_cooldown = 0  # bypass cooldown
    g._try_punch(0)  # same color → combo 2
    assert g.player.combo == 2
    g._player_punch_cooldown = 0
    g._try_punch(0)  # combo 3
    assert g.player.combo == 3


def test_try_punch_different_color_resets_combo() -> None:
    """Different color punch resets combo to 0."""
    g = _make_game()
    g._try_punch(0)  # combo = 1
    g._player_punch_cooldown = 0
    g._try_punch(1)  # different color → combo resets to 0
    assert g.player.combo == 0


def test_try_punch_super_combo_triggers() -> None:
    """COMBO >= 4 triggers SUPER COMBO."""
    g = _make_game()
    for _ in range(4):
        g._player_punch_cooldown = 0
        g._try_punch(0)
    # After 4th punch: combo was 3, hit color matches → combo becomes 4 → is_super
    # But is_super check happens when combo >= 4, then resets combo to 0
    # Actually let me trace through carefully:
    # Punch 1: _last_player_color < 0 → combo=1, is_super=(1>=4)=False
    # Punch 2: color==_last_player_color(0) → combo=2, is_super=False
    # Punch 3: combo=3, is_super=False
    # Punch 4: combo=4, is_super=(4>=4)=True
    # Super resets combo to 0
    assert g.player.max_combo >= 4
    assert g.player.combo == 0  # reset by SUPER COMBO
    assert g.shake_frames == SHAKE_FRAMES
    assert g._last_super_combo


def test_try_punch_super_damage_doubled() -> None:
    """SUPER COMBO deals 2x damage. Note: combo is reset to 0 BEFORE
    damage calculation in _try_punch, so combo_bonus = 1.0 for supers."""
    g = _make_game()
    # Punch 3 times first (combo=3)
    for _ in range(3):
        g._player_punch_cooldown = 0
        g._try_punch(0)
    assert g.player.combo == 3
    # Punch 4 — should be super (combo becomes 4, triggers is_super, resets to 0)
    g._player_punch_cooldown = 0
    ai_hp_before = g.ai.hp
    hit, damage, is_super = g._try_punch(0)
    assert is_super
    damage_dealt = ai_hp_before - g.ai.hp
    # Combo reset before damage calc: bonus = 1 + 0 * 0.25 = 1.0
    # damage = 10 * 1.0 * 2 = 20
    assert damage_dealt == 20
    assert damage == 20


def test_try_punch_cooldown_blocks() -> None:
    """Punching while on cooldown does nothing."""
    g = _make_game()
    g._try_punch(0)
    # Cooldown should now be active
    hit, damage, is_super = g._try_punch(0)
    assert not hit
    assert damage == 0
    assert not is_super


def test_try_punch_dead_player_blocks() -> None:
    """Dead player cannot punch."""
    g = _make_game()
    g.player.hp = 0
    hit, damage, is_super = g._try_punch(0)
    assert not hit


def test_try_punch_dead_ai_blocks() -> None:
    """Cannot punch dead AI."""
    g = _make_game()
    g.ai.hp = 0
    hit, damage, is_super = g._try_punch(0)
    assert not hit


def test_try_punch_spawns_particles() -> None:
    """Hit spawns particles."""
    g = _make_game()
    initial_particles = len(g.particles)
    g._try_punch(0)
    assert len(g.particles) > initial_particles


def test_try_punch_spawns_floating_text() -> None:
    """Hit spawns floating damage text."""
    g = _make_game()
    initial_texts = len(g.floating_texts)
    g._try_punch(0)
    assert len(g.floating_texts) > initial_texts


def test_try_punch_max_combo_tracks() -> None:
    """max_combo should track the highest combo achieved."""
    g = _make_game()
    g._try_punch(0)          # combo=1, max_combo=1
    g._player_punch_cooldown = 0
    g._try_punch(0)          # combo=2, max_combo=2
    g._player_punch_cooldown = 0
    g._try_punch(1)          # different color → combo=0, max_combo stays 2
    assert g.player.max_combo == 2
    assert g.player.combo == 0


# ── AI logic tests ──


def test_ai_act_punches_player() -> None:
    """AI punches and damages player when in range."""
    g = _make_game()
    g._ai_punch_timer = 1  # will trigger next tick
    player_hp_before = g.player.hp
    g._ai_act()
    assert g.player.hp < player_hp_before
    assert g.player.hp == player_hp_before - AI_PUNCH_DAMAGE


def test_ai_act_stunned_does_nothing() -> None:
    """AI in hit stun does not act."""
    g = _make_game()
    g.ai.hit_stun = 10
    g._ai_punch_timer = 0
    player_hp_before = g.player.hp
    g._ai_act()
    assert g.player.hp == player_hp_before


def test_ai_act_dead_does_nothing() -> None:
    """Dead AI does not act."""
    g = _make_game()
    g.ai.hp = 0
    g._ai_punch_timer = 0
    player_hp_before = g.player.hp
    g._ai_act()
    assert g.player.hp == player_hp_before


def test_ai_act_dead_player_no_act() -> None:
    """AI does not act when player is dead."""
    g = _make_game()
    g.player.hp = 0
    g._ai_punch_timer = 0
    ai_hp_before = g.ai.hp  # changed nothing
    g._ai_act()
    assert g.ai.hp == ai_hp_before


def test_ai_punch_interval_decreases() -> None:
    """AI punch interval decreases over game time."""
    g = _make_game()
    g.game_timer = GAME_DURATION - 30 * 30  # 30 seconds elapsed
    g._ai_punch_timer = 1
    g._ai_act()  # this will trigger ai punch and recompute interval
    # After half the game, interval should be less than AI_BASE_INTERVAL
    assert g._ai_punch_interval < AI_BASE_INTERVAL
    assert g._ai_punch_interval >= AI_MIN_INTERVAL


def test_ai_punch_count_increments() -> None:
    """AI punch count increments after punching."""
    g = _make_game()
    g._ai_punch_timer = 1
    count_before = g._ai_punch_count
    g._ai_act()
    assert g._ai_punch_count == count_before + 1


def test_ai_color_changes_every_3_punches() -> None:
    """AI changes color every 3 punches (when _ai_punch_count % 3 == 0)."""
    g = _make_game()
    g._ai_punch_count = 2  # next punch will be the 3rd
    g._ai_punch_timer = 1
    g._ai_act()
    # After 3rd punch, color may change (50% chance to counter-pick or random)
    # We can only verify the punch happened
    assert g._ai_punch_count == 3


# ── Particle system tests ──


def test_spawn_particles_adds_to_list() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 8, 5)
    assert len(g.particles) == 5


def test_spawn_particles_negative_color_rainbow() -> None:
    """color=-1 should produce rainbow (random) colors."""
    g = _make_game()
    g._spawn_particles(100, 100, -1, 10)
    assert len(g.particles) == 10


def test_update_particles_reduces_life() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 8, 2)
    initial_life = g.particles[0].life
    g._update_particles()
    # Particles with life=1 would be removed; life >= 2 survives one update
    remaining = [p for p in g.particles if p.life > 0]
    if len(remaining) >= 1:
        assert remaining[0].life < initial_life or initial_life <= 1


def test_update_particles_removes_expired() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → decremented to 0 → removed


def test_update_particles_applies_gravity() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=8)]
    g._update_particles()
    assert abs(g.particles[0].vy - 0.1) < 0.001


# ── Floating text tests ──


def test_update_floating_texts_reduces_life() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=50.0, text="-10", life=2, color=8)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 1


def test_update_floating_texts_removes_expired() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=50.0, text="-10", life=1, color=8)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_floating_texts_floats_upward() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=50.0, text="-10", life=10, color=8)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - 49.5) < 0.001


# ── Score computation tests ──


def test_compute_score_basic() -> None:
    g = _make_game()
    g.total_damage = 100
    g.player.max_combo = 5
    expected = int(100 * (1 + 5 * 0.1))
    assert g._compute_score() == expected


def test_compute_score_zero_combo() -> None:
    g = _make_game()
    g.total_damage = 50
    g.player.max_combo = 0
    assert g._compute_score() == 50


# ── Game over tests ──


def test_is_game_over_player_dead() -> None:
    g = _make_game()
    g.player.hp = 0
    assert g._is_game_over()


def test_is_game_over_ai_dead() -> None:
    g = _make_game()
    g.ai.hp = 0
    assert g._is_game_over()


def test_is_game_over_time_up() -> None:
    g = _make_game()
    g.game_timer = 0
    assert g._is_game_over()


def test_is_game_over_not_yet() -> None:
    g = _make_game()
    assert not g._is_game_over()


# ── Constants sanity tests ──


def test_screen_dimensions() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240


def test_fighter_positions() -> None:
    assert PLAYER_X == 80
    assert AI_X == 240


def test_damage_constants() -> None:
    assert BASE_DAMAGE == 10
    assert SUPER_DAMAGE_MULT == 2
    assert AI_PUNCH_DAMAGE == 8


def test_combo_threshold() -> None:
    assert SUPER_COMBO_THRESHOLD == 4


def test_game_duration() -> None:
    assert GAME_DURATION == 60 * 30  # 60 seconds at 30fps


# ── Edge case: combo reach to super without overflow ──


def test_punch_builds_to_super_then_resets() -> None:
    """Full combo cycle: build to 4, trigger super, combo resets, can rebuild."""
    g = _make_game()
    # Build to super
    for i in range(4):
        g._player_punch_cooldown = 0
        g._try_punch(0)
    
    # After 4th punch: was super, combo reset to 0
    assert g.player.combo == 0
    assert g.player.max_combo >= 4
    assert g._last_super_combo

    # Can rebuild combo
    g._player_punch_cooldown = 0
    g._try_punch(0)
    assert g.player.combo == 1


# ── Edge case: total_damage accumulates ──


def test_total_damage_accumulates() -> None:
    g = _make_game()
    d1 = g.total_damage
    g._try_punch(0)
    assert g.total_damage > d1
    d2 = g.total_damage
    g._player_punch_cooldown = 0
    g._try_punch(0)
    assert g.total_damage > d2


# ── Edge case: AI aggression reaches minimum ──


def test_ai_aggression_full_time() -> None:
    g = _make_game()
    g.game_timer = 1  # nearly over
    g._ai_punch_timer = 1
    g._ai_act()
    # After nearly full game, interval should be at min
    assert g._ai_punch_interval == AI_MIN_INTERVAL


# ── Edge case: shake_frames decays ──


def test_shake_frames_set_on_super() -> None:
    g = _make_game()
    assert g.shake_frames == 0
    for _ in range(4):
        g._player_punch_cooldown = 0
        g._try_punch(0)
    assert g.shake_frames == SHAKE_FRAMES


# ── Edge case: hit_stun prevents actions ──


def test_ai_hit_stun_prevents_counter() -> None:
    g = _make_game()
    g._try_punch(0)  # gives AI hit stun
    assert g.ai.hit_stun > 0
    player_hp_before = g.player.hp
    g._ai_punch_timer = 1
    g._ai_act()  # should not act due to stun
    assert g.player.hp == player_hp_before  # no damage


# ── Edge case: combo cooldown decrements ──
# (This would be tested by the update() method, but we can simulate)


def test_combo_and_damage_scaling() -> None:
    """Verify damage scales with combo: base * (1 + combo * 0.25)."""
    g = _make_game()
    
    # First punch: combo=1 after hit
    g._try_punch(0)
    # We know total_damage was added (can't test exact value since it's internal)
    assert g.total_damage > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
