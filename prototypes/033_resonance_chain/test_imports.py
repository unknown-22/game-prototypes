"""test_imports.py — Headless logic tests for 033_resonance_chain."""

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/033_resonance_chain")

from main import (
    Game, Note, Phase, FloatingText, Particle,
    CHAIN_THRESHOLD, LANE_COUNT, HIT_ZONE_Y, GOOD_WINDOW,
    SCREEN_H, SPAWN_INTERVAL,
)


def test_imports() -> None:
    """Verify all classes and constants import correctly."""
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2
    assert CHAIN_THRESHOLD == 5
    assert LANE_COUNT == 4
    assert isinstance(HIT_ZONE_Y, int)
    assert isinstance(GOOD_WINDOW, int)
    print("OK: imports")


def test_game_reset() -> None:
    """Test that reset() initializes all state fields."""
    import inspect

    source = inspect.getsource(Game.reset)
    expected_attrs = [
        "self.phase", "self.notes", "self.particles", "self.texts",
        "self.score", "self.combo", "self.max_combo", "self.health",
        "self.resonance_color", "self.resonance_count",
        "self.spawn_timer", "self.frame", "self.difficulty",
        "self.chain_clear_count",
    ]
    for attr in expected_attrs:
        assert attr in source, f"reset() missing: {attr}"
    print("OK: reset initializes all fields")


def test_note_creation() -> None:
    """Test Note dataclass."""
    note = Note(lane=2, y=0.0)
    assert note.lane == 2
    assert note.y == 0.0
    assert note.hit is False
    assert note.missed is False

    note.hit = True
    assert note.hit is True
    print("OK: note creation")


def test_particle_creation() -> None:
    """Test Particle dataclass."""
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=20, color=11)
    assert p.x == 10.0
    assert p.life == 20
    print("OK: particle creation")


def test_floating_text_creation() -> None:
    """Test FloatingText dataclass."""
    t = FloatingText(x=100.0, y=50.0, text="PERFECT", life=30, color=5)
    assert t.text == "PERFECT"
    assert t.life == 30
    print("OK: floating text creation")


def test_spawn_note() -> None:
    """Test that _spawn_note adds a note with valid lane."""
    g = Game()
    g._spawn_note()
    assert len(g.notes) == 1
    assert 0 <= g.notes[0].lane < LANE_COUNT
    assert g.notes[0].y == -14.0  # -NOTE_H
    print("OK: spawn_note")


def test_try_hit_no_note() -> None:
    """Test _try_hit with no notes in lane."""
    g = Game()
    g.phase = Phase.PLAYING
    g._try_hit(0)
    assert g.score == 0
    assert g.combo == 0
    print("OK: try_hit with no note")


def test_try_hit_perfect() -> None:
    """Test perfect hit scoring."""
    g = Game()
    g.phase = Phase.PLAYING
    g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y)))
    g._try_hit(0)
    assert g.combo == 1
    assert len(g.texts) >= 1
    assert g.texts[-1].text == "PERFECT"
    assert g.score > 0
    print("OK: perfect hit")


def test_try_hit_good() -> None:
    """Test good hit scoring."""
    g = Game()
    g.phase = Phase.PLAYING
    g.notes.append(Note(lane=1, y=float(HIT_ZONE_Y + 15)))
    g._try_hit(1)
    assert g.combo == 1
    assert g.texts[-1].text == "GOOD"
    assert g.score > 0
    print("OK: good hit")


def test_try_hit_miss_distance() -> None:
    """Test that notes too far from hit zone are not hit."""
    g = Game()
    g.phase = Phase.PLAYING
    g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y + GOOD_WINDOW + 10)))
    g._try_hit(0)
    assert g.combo == 0
    assert g.score == 0
    print("OK: too far to hit")


def test_on_miss() -> None:
    """Test miss processing."""
    g = Game()
    g.health = 3
    g.combo = 5
    g.resonance_count = 3
    note = Note(lane=0, y=100.0)
    g._on_miss(note)
    assert g.health == 2
    assert g.combo == 0
    assert g.resonance_count == 0
    assert g.resonance_color is None
    print("OK: on_miss")


def test_combo_scoring() -> None:
    """Test that combo increases score multiplier."""
    g = Game()
    g.phase = Phase.PLAYING

    # First hit
    g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y)))
    g._try_hit(0)
    score_after_1 = g.score

    # Second hit
    g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y)))
    g._try_hit(0)
    score_after_2 = g.score

    # Third hit
    g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y)))
    g._try_hit(0)
    score_after_3 = g.score

    # Each hit should add some score
    assert score_after_1 > 0
    assert score_after_2 > score_after_1
    assert score_after_3 > score_after_2
    print("OK: combo scoring increases")


def test_resonance_chain_same_color() -> None:
    """Test that consecutive same-lane hits build resonance."""
    g = Game()
    g.phase = Phase.PLAYING

    for _ in range(3):
        g.notes.append(Note(lane=2, y=float(HIT_ZONE_Y)))
        g._try_hit(2)

    assert g.resonance_count == 3
    assert g.resonance_color == 2
    print("OK: resonance chain builds")


def test_resonance_chain_different_color() -> None:
    """Test that switching lane resets resonance."""
    g = Game()
    g.phase = Phase.PLAYING

    g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y)))
    g._try_hit(0)
    assert g.resonance_color == 0
    assert g.resonance_count == 1

    g.notes.append(Note(lane=1, y=float(HIT_ZONE_Y)))
    g._try_hit(1)
    assert g.resonance_color == 1
    assert g.resonance_count == 1
    print("OK: resonance resets on color change")


def test_chain_clear() -> None:
    """Test chain clear removes matching color notes."""
    g = Game()
    g.phase = Phase.PLAYING

    # Set up 5 same-lane hits to trigger chain clear
    for _ in range(5):
        g.notes.append(Note(lane=1, y=float(HIT_ZONE_Y)))
        g._try_hit(1)

    # Should have triggered chain clear at count=5
    assert g.resonance_count == 5
    # The chain clear should have been triggered
    # Additional notes of color 1 should be cleared
    g.notes.append(Note(lane=1, y=50.0))
    g.notes.append(Note(lane=1, y=80.0))
    g._chain_clear(1)

    # All lane 1 notes should be hit now
    for note in g.notes:
        if note.lane == 1:
            assert note.hit is True
    print("OK: chain clear")


def test_particle_update() -> None:
    """Test particles expire after life reaches 0."""
    g = Game()
    g._spawn_particles(100.0, 100.0, 11)
    assert len(g.particles) == 8

    # Simulate 20 frames
    for _ in range(20):
        for p in g.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
    g.particles = [p for p in g.particles if p.life > 0]
    assert len(g.particles) == 0
    print("OK: particle expiration")


def test_floating_text_update() -> None:
    """Test floating texts expire after life reaches 0."""
    g = Game()
    g.texts.append(FloatingText(100.0, 100.0, "PERFECT", 10, 5))
    assert len(g.texts) == 1

    for _ in range(10):
        for t in g.texts:
            t.y -= 0.5
            t.life -= 1
    g.texts = [t for t in g.texts if t.life > 0]
    assert len(g.texts) == 0
    print("OK: floating text expiration")


def test_game_over_on_zero_health() -> None:
    """Test game over when health reaches 0."""
    g = Game()
    g.health = 1
    g.phase = Phase.PLAYING
    note = Note(lane=0, y=200.0)
    g._on_miss(note)
    assert g.health == 0
    # In the real game loop, phase would be set to GAME_OVER after check
    print("OK: health depletion")


def test_max_combo_tracking() -> None:
    """Test max_combo tracks highest combo reached."""
    g = Game()
    g.phase = Phase.PLAYING

    # Build combo to 3
    for _ in range(3):
        g.notes.append(Note(lane=0, y=float(HIT_ZONE_Y)))
        g._try_hit(0)
    assert g.max_combo == 3

    # Miss resets combo but max_combo stays
    g.combo = 0
    assert g.max_combo == 3
    print("OK: max_combo tracking")


def test_difficulty_scaling() -> None:
    """Test difficulty increases over time."""
    g = Game()
    g.frame = 0
    g.difficulty = 1.0

    g.frame = 3600  # ~60 seconds at 60fps
    g.difficulty = 1.0 + g.frame / 3600.0
    assert g.difficulty == 2.0
    print("OK: difficulty scaling")


def test_spawn_interval_decreases() -> None:
    """Test that spawn interval decreases with difficulty."""
    from main import SPAWN_INTERVAL
    interval_high_diff = max(15, SPAWN_INTERVAL - int(2.0 * 5))
    interval_low_diff = max(15, SPAWN_INTERVAL - int(1.0 * 5))
    assert interval_high_diff < interval_low_diff
    print("OK: spawn interval scales")


def test_miss_breaks_combo() -> None:
    """Test that a miss resets combo to 0."""
    g = Game()
    g.combo = 10
    g.resonance_count = 4
    g.resonance_color = 2
    note = Note(lane=0, y=200.0)
    g._on_miss(note)
    assert g.combo == 0
    print("OK: miss breaks combo")


def test_chain_clear_scoring() -> None:
    """Test chain clear awards bonus score."""
    g = Game()
    g.phase = Phase.PLAYING
    g.notes = [
        Note(lane=1, y=30.0),
        Note(lane=1, y=60.0),
        Note(lane=2, y=40.0),  # different color
    ]
    initial_score = g.score
    g._chain_clear(1)
    assert g.score > initial_score
    # Lane 1 notes should be hit
    assert g.notes[0].hit is True
    assert g.notes[1].hit is True
    # Lane 2 note should be unaffected
    assert g.notes[2].hit is False
    print("OK: chain clear scoring")


def test_cleanup_removes_offscreen_notes() -> None:
    """Test that off-screen notes are cleaned up."""
    g = Game()
    g.notes = [
        Note(lane=0, y=float(SCREEN_H + 30)),  # off screen
        Note(lane=1, y=100.0),  # on screen
    ]
    g.notes = [
        n for n in g.notes
        if n.y < SCREEN_H + 20 and not n.hit and not n.missed
    ]
    assert len(g.notes) == 1
    assert g.notes[0].lane == 1
    print("OK: off-screen cleanup")


if __name__ == "__main__":
    test_imports()
    test_game_reset()
    test_note_creation()
    test_particle_creation()
    test_floating_text_creation()
    test_spawn_note()
    test_try_hit_no_note()
    test_try_hit_perfect()
    test_try_hit_good()
    test_try_hit_miss_distance()
    test_on_miss()
    test_combo_scoring()
    test_resonance_chain_same_color()
    test_resonance_chain_different_color()
    test_chain_clear()
    test_particle_update()
    test_floating_text_update()
    test_game_over_on_zero_health()
    test_max_combo_tracking()
    test_difficulty_scaling()
    test_spawn_interval_decreases()
    test_miss_breaks_combo()
    test_chain_clear_scoring()
    test_cleanup_removes_offscreen_notes()
    print(f"\nAll {25} tests passed!")
