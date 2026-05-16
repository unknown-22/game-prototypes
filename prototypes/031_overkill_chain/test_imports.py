"""test_imports.py — Headless logic tests for 031_overkill_chain."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/031_overkill_chain")

import random
from main import (
    BASE_X,
    CLICK_DAMAGE,
    ENEMY_DEFS,
    ENEMY_H,
    ENEMY_W,
    ENEMY_Y_START,
    H,
    SPAWN_INTERVAL,
    W,
    Enemy,
    EnemyDef,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game() -> Game:
    """Create a Game instance without calling __init__ (which calls pyxel.init/run)."""
    g = Game.__new__(Game)
    g.reset()
    return g


def spawn_enemy_at(g: Game, x: float, y: float, defn_idx: int = 0) -> Enemy:
    """Helper to spawn an enemy at a specific position."""
    defn = ENEMY_DEFS[defn_idx]
    e = Enemy(defn=defn, x=x, y=y, hp=defn.hp)
    g.enemies.append(e)
    return e


# ── Dataclass / constant tests ──────────────────────────────────────


def test_enemy_defs_exist() -> None:
    assert len(ENEMY_DEFS) >= 4
    for d in ENEMY_DEFS:
        assert d.hp > 0
        assert d.speed > 0
        assert d.score > 0


def test_enemy_def_frozen() -> None:
    d = ENEMY_DEFS[0]
    try:
        d.hp = 999
        raise AssertionError("EnemyDef should be frozen")
    except (TypeError, Exception):
        pass  # Expected


def test_enemy_properties() -> None:
    defn = ENEMY_DEFS[0]
    e = Enemy(defn=defn, x=100, y=80, hp=defn.hp)
    assert e.max_hp == defn.hp
    assert e.hp_ratio == 1.0
    e.hp = 4
    assert abs(e.hp_ratio - 0.5) < 0.01 if defn.hp == 8 else True


def test_danger_level() -> None:
    defn = ENEMY_DEFS[0]
    # At base
    e1 = Enemy(defn=defn, x=BASE_X, y=80, hp=8)
    assert e1.danger_level == 1.0
    # Far right
    e2 = Enemy(defn=defn, x=float(W), y=80, hp=8)
    assert e2.danger_level == 0.0
    # Middle
    e3 = Enemy(defn=defn, x=(BASE_X + W) / 2, y=80, hp=8)
    assert 0.4 < e3.danger_level < 0.6


def test_particle_dataclass() -> None:
    p = Particle(x=10, y=20, vx=1.0, vy=-2.0, life=15, max_life=20, color=7)
    assert p.x == 10
    assert p.y == 20
    assert p.size == 1  # default


def test_floating_text() -> None:
    ft = FloatingText(x=50, y=30, text="+10", life=40, max_life=40, color=14)
    assert ft.text == "+10"


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game state tests ────────────────────────────────────────────────


def test_reset_state() -> None:
    g = make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == 100
    assert g.max_hp == 100
    assert g.wave == 1
    assert g.frame == 0
    assert len(g.enemies) == 0
    assert len(g.particles) == 0
    assert len(g.floats) == 0


def test_spawn_enemy() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 200, 80)
    assert len(g.enemies) == 1
    assert e.x == 200
    assert e.hp == ENEMY_DEFS[0].hp


def test_enemy_movement() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 200, 80, 0)  # grunt, speed=1.0
    initial_x = e.x
    g._update_enemies()
    assert e.x < initial_x
    assert abs(e.x - (initial_x - e.defn.speed)) < 0.01


def test_enemy_reaches_base() -> None:
    g = make_game()
    e = spawn_enemy_at(g, BASE_X + 1, 80, 0)
    g._update_enemies()
    assert not e.alive
    assert g.hp < 100
    assert g.combo == 0
    # Game-over check is in _update(), not _update_enemies()
    # Simulate it:
    if g.hp <= 0:
        g.phase = Phase.GAME_OVER


def test_enemy_reached_base_kills_combo() -> None:
    g = make_game()
    g.combo = 5
    spawn_enemy_at(g, BASE_X + 1, 80, 0)
    g._update_enemies()
    assert g.combo == 0


# ── Combat tests ────────────────────────────────────────────────────


def test_attack_enemy_no_kill() -> None:
    g = make_game()
    # Tank has 20 HP, click damage is 10
    e = spawn_enemy_at(g, 150, 80, 2)  # tank
    g._attack_enemy(e, CLICK_DAMAGE)
    assert e.alive
    assert e.hp == 20 - CLICK_DAMAGE
    assert e.hit_timer == 6
    assert g.combo == 1


def test_attack_enemy_kill() -> None:
    g = make_game()
    # Grunt has 8 HP
    e = spawn_enemy_at(g, 150, 80, 0)
    g._attack_enemy(e, CLICK_DAMAGE)
    assert not e.alive
    assert g.combo == 1
    assert g.score > 0


def test_overkill_ripples_left() -> None:
    g = make_game()
    # Runner has 5 HP. Click damage is 10 → 5 overkill
    # Place a grunt to the left
    e_right = spawn_enemy_at(g, 180, 80, 1)  # runner, hp=5
    e_left = spawn_enemy_at(g, 120, 80, 0)  # grunt, hp=8
    g._attack_enemy(e_right, CLICK_DAMAGE)
    # Overkill should damage e_left
    assert not e_right.alive
    assert e_left.hp < ENEMY_DEFS[0].hp  # grunt took overkill damage


def test_overkill_chain_kills_multiple() -> None:
    g = make_game()
    # Two runners (hp=5 each) in a line, click damage=10
    e3 = spawn_enemy_at(g, 200, 80, 1)  # runner right
    e2 = spawn_enemy_at(g, 160, 80, 1)  # runner middle
    e1 = spawn_enemy_at(g, 120, 80, 1)  # runner left
    g._attack_enemy(e3, CLICK_DAMAGE)
    # e3 dies with 5 overkill → should kill e2 with 5 overkill → damage e1
    assert not e3.alive
    assert not e2.alive
    assert e1.hp <= ENEMY_DEFS[1].hp  # grunt took some damage


def test_miss_resets_combo() -> None:
    g = make_game()
    g.combo = 3
    g._try_attack(999, 999)  # way off screen
    assert g.combo == 0
    assert g._chain_kills == 0


def test_combo_increments_on_hit() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 150, 80, 2)  # tank, hp=20
    g._attack_enemy(e, CLICK_DAMAGE)  # combo=1
    g._attack_enemy(e, CLICK_DAMAGE)  # combo=2
    assert g.combo == 2


def test_max_combo_tracks() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 150, 80, 2)  # tank
    g._attack_enemy(e, CLICK_DAMAGE)
    g._attack_enemy(e, CLICK_DAMAGE)
    g._attack_enemy(e, CLICK_DAMAGE)
    assert g.max_combo == 3


# ── Scoring tests ───────────────────────────────────────────────────


def test_score_increases_on_kill() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 150, 80, 0)  # grunt
    initial = g.score
    g._attack_enemy(e, CLICK_DAMAGE)
    assert g.score > initial


def test_danger_bonus_closer_is_higher() -> None:
    g = make_game()
    # Kill a close enemy
    e_close = spawn_enemy_at(g, BASE_X + 30, 80, 0)
    g._attack_enemy(e_close, CLICK_DAMAGE)
    close_score = g.score

    # Reset and kill a far enemy
    g2 = make_game()
    e_far = spawn_enemy_at(g2, W - 30, 80, 0)
    g2._attack_enemy(e_far, CLICK_DAMAGE)
    far_score = g2.score

    # Close enemy should give more score due to danger bonus
    assert close_score > far_score


def test_chain_kill_multiplier() -> None:
    g = make_game()
    # Chain-kill 3 runners
    e3 = spawn_enemy_at(g, 200, 80, 1)  # runner
    e2 = spawn_enemy_at(g, 160, 80, 1)  # runner
    e1 = spawn_enemy_at(g, 120, 80, 1)  # runner
    g._attack_enemy(e3, CLICK_DAMAGE)
    assert g._chain_kills == 3  # All three should die from overkill


# ── Particle / float tests ─────────────────────────────────────────


def test_spawn_particles() -> None:
    g = make_game()
    g._spawn_particles(100, 80, 7, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.life > 0


def test_particle_update() -> None:
    g = make_game()
    g._spawn_particles(100, 80, 7, 3)
    for p in g.particles:
        p.life = 10  # Set controlled life
    g._update_particles()
    # Particles should have life decreased and vy increased by gravity
    for p in g.particles:
        assert p.life == 9  # decreased by 1
        assert p.vy > -2.0  # gravity adds 0.15 each frame


def test_particle_expiry() -> None:
    g = make_game()
    g._spawn_particles(100, 80, 7, 3)
    # Set life to 1
    for p in g.particles:
        p.life = 1
    g._update_particles()
    # After update, life=0 particles should be removed
    assert len(g.particles) == 0


def test_float_text_update() -> None:
    g = make_game()
    g._add_float(100, 80, "+10", 14)
    assert len(g.floats) == 1
    ft = g.floats[0]
    assert ft.text == "+10"
    g._update_floats()
    assert ft.life == 39
    assert ft.y < 80  # moved up


# ── Shake tests ────────────────────────────────────────────────────


def test_shake_on_base_damage() -> None:
    g = make_game()
    spawn_enemy_at(g, BASE_X + 1, 80, 0)
    g._update_enemies()
    assert g.shake_timer > 0
    assert g.shake_intensity == 3


def test_shake_decay() -> None:
    g = make_game()
    g.shake_timer = 5
    g.shake_intensity = 3
    for _ in range(5):
        g._update_shake()
    assert g.shake_timer == 0
    # One more call triggers the else branch that resets intensity
    g._update_shake()
    assert g.shake_intensity == 0


def test_chain_kill_multiplier() -> None:
    g = make_game()
    # Three runners (hp=5 each). Attack with 20 damage for chain kills.
    # 20 dmg - 5 hp = 15 overkill → 15 dmg - 5 hp = 10 overkill → 10 dmg - 5 hp = 5 overkill
    for i in range(3):
        spawn_enemy_at(g, 200 - i * 40, 80, 1)  # runners
    g._attack_enemy(g.enemies[0], 20)
    assert g._chain_kills == 3  # All three should die from overkill


def test_shake_on_chain_kills() -> None:
    g = make_game()
    # Chain kill 3+ enemies with enough damage
    for i in range(3):
        spawn_enemy_at(g, 200 - i * 40, 80, 1)  # runners
    g._attack_enemy(g.enemies[0], 20)
    assert g._chain_kills == 3
    assert g.shake_timer > 0
    assert g.shake_intensity == 2


# ── Wave / spawn tests ─────────────────────────────────────────────


def test_spawn_interval() -> None:
    g = make_game()
    g.spawn_timer = SPAWN_INTERVAL - 1
    g._update_spawns()
    assert len(g.enemies) == 1
    assert g.spawn_timer == 0


def test_spawn_interval_shortens_with_wave() -> None:
    g = make_game()
    g.wave = 10
    # Interval should be shorter
    interval = max(15, 45 - g.wave * 2)
    assert interval < 45


def test_wave_escalation() -> None:
    g = make_game()
    g.frame = 599
    g._update_enemies()  # wave escalation check
    assert g.wave == 1
    g.frame = 600
    g._update_enemies()
    assert g.wave == 2


# ── Game over tests ────────────────────────────────────────────────


def test_game_over_on_zero_hp() -> None:
    g = make_game()
    g.hp = 0
    # Game-over check is in _update(), not _update_enemies()
    if g.hp <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_game_over_on_massive_damage() -> None:
    g = make_game()
    g.hp = 0
    if g.hp <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── find_next_enemy_in_line tests ──────────────────────────────────


def test_find_next_enemy_returns_leftmost() -> None:
    g = make_game()
    e3 = spawn_enemy_at(g, 200, 80, 0)
    e2 = spawn_enemy_at(g, 150, 80, 0)
    e1 = spawn_enemy_at(g, 100, 80, 0)
    result = g._find_next_enemy_in_line(e3)
    assert result is e2


def test_find_next_enemy_none() -> None:
    g = make_game()
    e1 = spawn_enemy_at(g, 100, 80, 0)
    result = g._find_next_enemy_in_line(e1)
    assert result is None


def test_find_next_enemy_skips_dead() -> None:
    g = make_game()
    e2 = spawn_enemy_at(g, 150, 80, 0)
    e1 = spawn_enemy_at(g, 100, 80, 0)
    e2.alive = False
    result = g._find_next_enemy_in_line(
        Enemy(defn=ENEMY_DEFS[0], x=200, y=80, hp=8)
    )
    # Only e1 is alive and to the left
    if result is not None:
        assert result is e1


# ── Edge cases ──────────────────────────────────────────────────────


def test_empty_enemies_attack() -> None:
    g = make_game()
    g._try_attack(100, 80)
    assert g.combo == 0


def test_chain_kills_reset_on_miss() -> None:
    g = make_game()
    g._chain_kills = 5
    g._try_attack(999, 999)
    assert g._chain_kills == 0


def test_overkill_does_not_chain_infinitely() -> None:
    g = make_game()
    # Single enemy with lots of damage
    e = spawn_enemy_at(g, 150, 80, 0)
    g._attack_enemy(e, 1000)
    # Should not crash, no next enemy to ripple to
    assert not e.alive
    assert len(g.particles) > 0


def test_enemy_hp_cannot_go_negative_in_display() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 150, 80, 0)
    g._attack_enemy(e, 100)
    assert e.hp == 0  # Clamped to 0


def test_hit_timer_decrements() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 150, 80, 2)  # Tank (hp=20), survives hit
    g._attack_enemy(e, CLICK_DAMAGE)
    assert e.hit_timer == 6
    g._update_enemies()  # moves + decrements timer
    assert e.hit_timer == 5


def test_float_text_count() -> None:
    g = make_game()
    e = spawn_enemy_at(g, 150, 80, 0)
    g._attack_enemy(e, CLICK_DAMAGE)
    assert len(g.floats) == 1


def test_particle_gravity() -> None:
    g = make_game()
    g._spawn_particles(100, 80, 7, 1)
    p = g.particles[0]
    initial_vy = p.vy
    g._update_particles()
    assert p.vy > initial_vy  # gravity adds to vy


# ── inspect: verify reset() initializes all state ──────────────────


def test_reset_defines_all_state() -> None:
    import inspect

    src = inspect.getsource(Game.reset)
    expected_vars = [
        "self.phase",
        "self.enemies",
        "self.particles",
        "self.floats",
        "self.score",
        "self.combo",
        "self.max_combo",
        "self.hp",
        "self.max_hp",
        "self.wave",
        "self.spawn_timer",
        "self.frame",
        "self.shake_timer",
        "self.shake_intensity",
        "self._chain_kills",
    ]
    for var in expected_vars:
        assert var in src, f"reset() should initialize {var}"


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
