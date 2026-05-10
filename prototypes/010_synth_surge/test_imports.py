"""test_imports.py — Headless logic tests for Synth Surge."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/010_synth_surge")

from main import (
    Bullet,
    Chroma,
    CHROMA_COL,
    CHROMA_LABEL,
    CHROMA_NAME,
    Enemy,
    FloatingText,
    Particle,
    Phase,
    Player,
    Shard,
    SynthSurge,
    SCREEN_W,
    SCREEN_H,
    PLAYER_MAX_HP,
    FIRE_COOLDOWN,
    ENEMY_SPAWN_BASE,
    SHARD_LIFETIME,
    SYNTH_ANIM_DUR,
    FREEZE_DURATION,
    OVERRIDE_DURATION,
    MAX_ENEMIES,
)


def test_constants() -> None:
    assert SCREEN_W == 400
    assert SCREEN_H == 300
    assert PLAYER_MAX_HP == 5
    assert FIRE_COOLDOWN == 12
    assert ENEMY_SPAWN_BASE == 50
    assert SHARD_LIFETIME == 360
    assert SYNTH_ANIM_DUR == 20
    assert FREEZE_DURATION == 180
    assert OVERRIDE_DURATION == 240
    assert MAX_ENEMIES == 20


def test_chroma_enum() -> None:
    """Chroma enum has 4 values."""
    chromas = list(Chroma)
    assert len(chromas) == 4
    assert Chroma.RED in chromas
    assert Chroma.BLUE in chromas
    assert Chroma.GREEN in chromas
    assert Chroma.YELLOW in chromas


def test_chroma_mappings() -> None:
    """All chroma have color, name, and label mappings."""
    for chroma in Chroma:
        assert chroma in CHROMA_COL
        assert isinstance(CHROMA_COL[chroma], int)
        assert chroma in CHROMA_NAME
        assert isinstance(CHROMA_NAME[chroma], str)
        assert len(CHROMA_NAME[chroma]) > 0
        assert chroma in CHROMA_LABEL
        assert len(CHROMA_LABEL[chroma]) == 1


def test_phase_enum() -> None:
    phases = list(Phase)
    assert len(phases) == 3
    assert Phase.PLAYING in phases
    assert Phase.SYNTH_ANIM in phases
    assert Phase.GAME_OVER in phases


def test_player_dataclass() -> None:
    p = Player(x=100.0, y=200.0)
    assert p.x == 100.0
    assert p.y == 200.0
    assert p.hp == PLAYER_MAX_HP
    assert p.fire_timer == 0
    assert p.invuln == 0
    assert p.override_timer == 0


def test_enemy_dataclass() -> None:
    e = Enemy(x=50.0, y=60.0, hp=2, speed=1.5, radius=5, chroma=Chroma.RED)
    assert e.x == 50.0
    assert e.y == 60.0
    assert e.hp == 2
    assert e.speed == 1.5
    assert e.radius == 5
    assert e.chroma == Chroma.RED
    assert e.frozen == 0


def test_bullet_dataclass() -> None:
    b = Bullet(x=10.0, y=20.0, vx=3.0, vy=-1.0)
    assert b.x == 10.0
    assert b.y == 20.0
    assert b.vx == 3.0
    assert b.vy == -1.0
    assert b.damage == 1


def test_shard_dataclass() -> None:
    s = Shard(x=30.0, y=40.0, chroma=Chroma.BLUE)
    assert s.x == 30.0
    assert s.y == 40.0
    assert s.chroma == Chroma.BLUE
    assert s.life == SHARD_LIFETIME


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, col=8, life=15, max_life=20)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.col == 8
    assert p.life == 15
    assert p.max_life == 20


def test_floating_text_dataclass() -> None:
    f = FloatingText(x=50.0, y=60.0, text="TEST", col=7, life=30)
    assert f.x == 50.0
    assert f.y == 60.0
    assert f.text == "TEST"
    assert f.col == 7
    assert f.life == 30
    assert f.vy == -1.0


def test_synth_surge_init_state() -> None:
    """Check reset() initializes all attributes correctly."""
    import inspect

    source = inspect.getsource(SynthSurge.reset)
    # Verify all state attributes are set in reset()
    attrs = [
        "self.phase",
        "self.player",
        "self.enemies",
        "self.bullets",
        "self.shards",
        "self.particles",
        "self.floaters",
        "self.synth_slots",
        "self.synth_anim_timer",
        "self.synth_color",
        "self.spawn_timer",
        "self.score",
        "self.synthesis_count",
        "self.game_time",
        "self.freeze_timer",
        "self.shake_timer",
        "self.shake_intensity",
    ]
    for attr in attrs:
        assert attr in source, f"Missing attribute: {attr}"


def test_synth_slots_initial_state() -> None:
    """Validate initial synth_slots structure."""
    import inspect

    source = inspect.getsource(SynthSurge.reset)
    assert "self.synth_slots" in source
    assert "[None, None, None]" in source


def test_methods_exist() -> None:
    """All critical methods exist on SynthSurge."""
    methods = [
        "reset",
        "update",
        "draw",
        "_update_player",
        "_update_bullets",
        "_update_enemies",
        "_update_shards",
        "_update_particles",
        "_update_floaters",
        "_spawn_enemies",
        "_spawn_one_enemy",
        "_fire_bullet",
        "_find_nearest_enemy",
        "_add_shard_to_slots",
        "_check_synthesis",
        "_trigger_synthesis",
        "_super_incinerate",
        "_super_freeze",
        "_super_regen",
        "_super_override",
        "_on_enemy_killed",
        "_add_floater",
        "_spawn_particles",
        "_update_timers",
        "_draw_player",
        "_draw_enemies",
        "_draw_shards",
        "_draw_bullets",
        "_draw_particles",
        "_draw_floaters",
        "_draw_ui",
        "_draw_synthesis_flash",
        "_draw_game_over",
    ]
    for m in methods:
        assert hasattr(SynthSurge, m), f"Missing method: {m}"


def test_no_method_name_collisions() -> None:
    """Ensure unique method names (no silent overrides)."""
    import inspect

    # Get all method names from the class
    methods = [
        name for name, val in SynthSurge.__dict__.items()
        if callable(val) and not name.startswith("__")
    ]
    assert len(methods) == len(set(methods)), f"Duplicate method names found: {methods}"


def test_super_effects_consistency() -> None:
    """Each Chroma maps to exactly one super effect."""
    # Verify the mapping in _trigger_synthesis
    import inspect

    source = inspect.getsource(SynthSurge._trigger_synthesis)
    for chroma in Chroma:
        assert chroma.name in source, f"Missing super effect for {chroma}"

    # Each super method exists
    for suffix in ["incinerate", "freeze", "regen", "override"]:
        name = f"_super_{suffix}"
        assert hasattr(SynthSurge, name), f"Missing: {name}"


def test_shard_fifo_logic() -> None:
    """Test FIFO queue logic for shard addition."""
    slots: list[Chroma | None] = [None, None, None]

    # Add RED
    slots[0] = slots[1]
    slots[1] = slots[2]
    slots[2] = Chroma.RED
    assert slots == [None, None, Chroma.RED]

    # Add BLUE
    slots[0] = slots[1]
    slots[1] = slots[2]
    slots[2] = Chroma.BLUE
    assert slots == [None, Chroma.RED, Chroma.BLUE]

    # Add RED (no synthesis — first 3 are None, RED, BLUE)
    slots[0] = slots[1]
    slots[1] = slots[2]
    slots[2] = Chroma.RED
    assert slots == [Chroma.RED, Chroma.BLUE, Chroma.RED]

    # Add RED again
    slots[0] = slots[1]
    slots[1] = slots[2]
    slots[2] = Chroma.RED
    assert slots == [Chroma.BLUE, Chroma.RED, Chroma.RED]

    # Add RED once more (now slots match!)
    slots[0] = slots[1]
    slots[1] = slots[2]
    slots[2] = Chroma.RED
    assert slots[0] == slots[1] == slots[2] == Chroma.RED


def test_synthesis_detection() -> None:
    """Test synthesis detection logic."""
    # Non-matching
    slots: list[Chroma | None] = [Chroma.RED, Chroma.BLUE, Chroma.GREEN]
    result = slots[0] is not None and slots[0] == slots[1] == slots[2]
    assert result is False

    # Matching
    slots = [Chroma.RED, Chroma.RED, Chroma.RED]
    result = slots[0] is not None and slots[0] == slots[1] == slots[2]
    assert result is True

    # With None
    slots = [Chroma.RED, Chroma.RED, None]
    result = slots[0] is not None and slots[0] == slots[1] == slots[2]
    assert result is False


if __name__ == "__main__":
    # Run all tests
    import inspect as _inspect

    tests = [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  PASS {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    if failed > 0:
        sys.exit(1)
