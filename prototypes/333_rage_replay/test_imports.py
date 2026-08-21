"""test_imports.py — Headless logic tests for 333_rage_replay.

Imports the game module without initializing Pyxel (the `if __name__ == "__main__"`
guard prevents pyxel.init/pyxel.run), and tests pure logic via Game.__new__(Game).
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    BOSS_HP,
    BOSS_SHOT_BASE_SPEED,
    GAME_DURATION,
    MAX_REPLAY,
    PLAYER_COOLDOWN,
    PLAYER_HP,
    PLAYER_SHOT_SPEED,
    Game,
    Phase,
    boss_fire_interval,
    boss_projectile_speed,
    player_damage_per_hit,
    rage_decay_per_frame,
    rage_gain_per_hit,
)


def make_game(seed: int = 42) -> Game:
    """Headless factory: bypass __init__ (no pyxel.init), seed the RNG, reset()."""
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


def test_boss_fire_interval_decreases_with_rage_and_enrage() -> None:
    assert boss_fire_interval(0.0, 0) == 50
    assert boss_fire_interval(100.0, 0) == 20
    assert boss_fire_interval(0.0, 3) == 38
    assert boss_fire_interval(100.0, 20) == 16  # floor


def test_boss_projectile_speed_scales() -> None:
    assert boss_projectile_speed(0) == BOSS_SHOT_BASE_SPEED
    assert boss_projectile_speed(3) == 1.8 + 3 * 0.4


def test_constants() -> None:
    assert rage_gain_per_hit() == 8
    assert rage_decay_per_frame() == 0.25
    assert player_damage_per_hit() == 4


def test_reset_initializes_state() -> None:
    g = make_game()
    assert g.phase is Phase.TITLE
    assert g.frame == 0
    assert g.player_hp == PLAYER_HP
    assert g.boss_hp == BOSS_HP
    assert g.rage == 0.0
    assert g.enrage_count == 0
    assert g.invincible_timer == 0
    assert g.replay_log == []
    assert g.projectiles == []
    assert g.score == 0
    assert g.victory is False
    assert g.defeat_reason == ""
    assert g.best_score >= 0


def test_fire_player_spawns_aimed_projectile() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 200.0
    g.boss_x = 100.0
    g.boss_y = 100.0
    g._fire_player()
    assert g.player_cooldown == PLAYER_COOLDOWN
    assert len(g.projectiles) == 1
    p = g.projectiles[0]
    assert p.kind == "player"
    # boss is directly above -> velocity points straight up (negative y)
    assert p.vx == 0.0
    assert p.vy == -PLAYER_SHOT_SPEED


def test_fire_player_respects_cooldown() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_cooldown = 5
    before = len(g.projectiles)
    g._fire_player()
    assert len(g.projectiles) == before
    assert g.player_cooldown == 5


def test_update_player_clamps_to_bounds() -> None:
    g = make_game()
    g.player_x = 6.0
    g._update_player(-1.0, 0.0)
    assert g.player_x == 6  # PLAYER_RADIUS clamp
    g.player_x = 320 - 6
    g.player_y = 240 - 6
    g._update_player(1.0, 1.0)
    assert g.player_x == 320 - 6
    assert g.player_y == 240 - 6


def test_check_boss_hit_damages_and_logs() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.boss_x = 160.0
    g.boss_y = 160.0
    g.boss_hp = BOSS_HP
    g.rage = 0.0
    # player projectile right on top of boss
    from main import Projectile

    g.projectiles.append(Projectile(160.0, 160.0, 0.0, 0.0, 3, "player", 100))
    hit = g._check_boss_hit()
    assert hit is True
    assert g.boss_hp == BOSS_HP - 4
    assert g.rage == 8.0
    assert g.score == 10
    assert len(g.replay_log) == 1


def test_check_boss_hit_invincible_no_damage() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.boss_x = 160.0
    g.boss_y = 160.0
    g.invincible_timer = 10
    from main import Projectile

    g.projectiles.append(Projectile(160.0, 160.0, 0.0, 0.0, 3, "player", 100))
    hit = g._check_boss_hit()
    assert hit is False
    assert g.boss_hp == BOSS_HP
    assert g.rage == 0.0
    assert g.replay_log == []
    # projectile removed anyway
    assert len(g.projectiles) == 0


def test_check_player_hit_reduces_hp_and_shakes() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    from main import Projectile

    g.projectiles.append(Projectile(100.0, 100.0, 0.0, 0.0, 4, "boss", 100))
    hit = g._check_player_hit()
    assert hit is True
    assert g.player_hp == PLAYER_HP - 1
    assert g.shake_frames > 0
    assert len(g.projectiles) == 0


def test_update_rage_decays_but_not_below_zero() -> None:
    g = make_game()
    g.rage = 0.1
    g._update_rage()
    assert g.rage == 0.0  # clamped at 0
    g.rage = 50.0
    g._update_rage()
    assert g.rage == 50.0 - 0.25


def test_update_rage_triggers_enrage_at_threshold() -> None:
    g = make_game()
    g.rage = 100.0
    g._update_rage()
    assert g.invincible_timer > 0
    assert g.enrage_count == 1
    assert g.rage == 0.0


def test_trigger_enrage_sets_state() -> None:
    g = make_game()
    g.rage = 100.0
    g._trigger_enrage()
    assert g.invincible_timer == 60
    assert g.enrage_count == 1
    assert g.rage == 0.0


def test_enrage_timers_fire_volley() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.replay_log = [(0.0, 0.0) for _ in range(5)]
    g.invincible_timer = 1
    g.player_x = 160.0
    g.player_y = 100.0
    g.boss_x = 160.0
    g.boss_y = 160.0
    g._update_enrage_timers()
    assert len(g.projectiles) == 5
    assert g.replay_log == []
    for p in g.projectiles:
        assert p.kind == "boss"


def test_fire_replay_volley_caps_and_guards_empty() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_x = 200.0
    g.player_y = 100.0
    g.boss_x = 160.0
    g.boss_y = 160.0
    # empty log -> 1 centered/aimed shot
    g._fire_replay_volley()
    assert len(g.projectiles) == 1
    g.projectiles.clear()
    # over-cap -> capped at MAX_REPLAY
    g.replay_log = [(0.0, 0.0)] * (MAX_REPLAY + 50)
    g._fire_replay_volley()
    assert len(g.projectiles) == MAX_REPLAY
    assert g.replay_log == []


def test_check_game_over_victory() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.boss_hp = 0
    g.score = 10
    g.frame = 100
    g._check_game_over()
    assert g.phase is Phase.GAME_OVER
    assert g.victory is True
    assert g.defeat_reason == "VICTORY"
    assert g.score == 10 + 1000 + (GAME_DURATION - 100) + 500


def test_check_game_over_defeated() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_hp = 0
    g._check_game_over()
    assert g.phase is Phase.GAME_OVER
    assert g.victory is False
    assert g.defeat_reason == "DEFEATED"


def test_check_game_over_time_up() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.frame = GAME_DURATION
    g._check_game_over()
    assert g.phase is Phase.GAME_OVER
    assert g.defeat_reason == "TIME UP"


def test_check_game_over_updates_best_score() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.player_hp = 0
    g._check_game_over()
    assert g.best_score == 500


def test_advance_increments_frame_and_reaches_time_up() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.frame = GAME_DURATION - 1
    g._advance()
    assert g.frame == GAME_DURATION
    assert g.phase is Phase.GAME_OVER
    assert g.defeat_reason == "TIME UP"


def test_advance_boss_fires_shot() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.boss_fire_timer = 0
    g._advance()
    boss_shots = [p for p in g.projectiles if p.kind == "boss"]
    assert len(boss_shots) >= 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
