"""test_imports.py — headless logic tests for TRIAGE: ER Shift (328_triage).

Imports the game module WITHOUT running pyxel (no display). Uses the
`_make_game(seed)` factory provided by main.py to bypass `Game.__init__`.
"""

import random

from main import (
    GAME_DURATION,
    SLOTS,
    START_REP,
    TREAT_TIME,
    Particle,
    Patient,
    PatientState,
    Phase,
    Severity,
    _make_game,
)


# --- Factory & enums ---


def test_factory_starts_in_title():
    g = _make_game(42)
    assert g.phase is Phase.TITLE
    assert g.score == 0
    assert g.rep == START_REP
    assert g.frame == 0
    assert g.saved_count == 0
    assert g.crashed_count == 0
    assert g.treating_slot is None
    assert len(g.slots) == SLOTS
    assert all(s is None for s in g.slots)


def test_enum_identity_from_main():
    assert Severity.MINOR.value == 1
    assert Severity.CRITICAL.value == 3
    assert PatientState.WAITING is PatientState.WAITING


# --- Pips signal (noisy, clamped 1..4) ---


def test_pips_always_within_bounds():
    g = _make_game(42)
    rng = random.Random(7)
    for _ in range(2000):
        p = g._make_patient(Severity.CRITICAL, rng)
        assert 1 <= p.pips <= 4
        p = g._make_patient(Severity.MINOR, rng)
        assert 1 <= p.pips <= 4
        p = g._make_patient(Severity.MODERATE, rng)
        assert 1 <= p.pips <= 4


def test_pips_correlate_with_severity():
    # Critical can reach 4; minor can never exceed 2.
    g = _make_game(42)
    rng = random.Random(11)
    minor_pips = [g._make_patient(Severity.MINOR, rng).pips for _ in range(300)]
    crit_pips = [g._make_patient(Severity.CRITICAL, rng).pips for _ in range(300)]
    assert max(minor_pips) <= 2
    assert max(crit_pips) >= 3
    assert sum(crit_pips) / len(crit_pips) > sum(minor_pips) / len(minor_pips)


def test_crash_timer_scaled_by_severity():
    g = _make_game(42)
    rng = random.Random(3)
    minor = [g._make_patient(Severity.MINOR, rng).crash_timer for _ in range(100)]
    crit = [g._make_patient(Severity.CRITICAL, rng).crash_timer for _ in range(100)]
    assert min(minor) > max(crit)


# --- Escalation curves ---


def test_timer_scale_curve():
    g = _make_game(42)
    g.frame = 0
    assert abs(g._timer_scale() - 1.0) < 1e-9
    g.frame = GAME_DURATION
    assert abs(g._timer_scale() - 0.7) < 1e-9


def test_spawn_interval_curve():
    g = _make_game(42)
    g.frame = 0
    assert g._spawn_interval() == 90
    g.frame = GAME_DURATION
    assert g._spawn_interval() == 30


def test_severity_weights_escalate_critical():
    g = _make_game(42)
    g.frame = 0
    minor0, mod0, crit0 = g._severity_weights()
    g.frame = GAME_DURATION
    minor1, mod1, crit1 = g._severity_weights()
    assert crit1 > crit0
    assert minor1 < minor0
    assert mod1 == mod0 == 3.0


# --- Spawning ---


def test_spawn_fills_one_slot():
    g = _make_game(42)
    g._spawn_patient()
    filled = [s for s in g.slots if s is not None]
    assert len(filled) == 1
    assert filled[0].state is PatientState.WAITING
    assert 1 <= filled[0].pips <= 4


def test_spawn_noop_when_full():
    g = _make_game(42)
    for i in range(SLOTS):
        g.slots[i] = Patient(Severity.MINOR, 1, 1000)
    g._spawn_patient()
    assert all(s is not None and s.pips == 1 for s in g.slots)


# --- Treatment ---


def test_start_treatment_success():
    g = _make_game(42)
    p = Patient(Severity.CRITICAL, 4, 300)
    g.slots[0] = p
    assert g._start_treatment(0) is True
    assert p.state is PatientState.TREATING
    assert g.treating_slot == 0
    assert g.treat_timer == TREAT_TIME


def test_start_treatment_rejects_when_busy():
    g = _make_game(42)
    g.slots[0] = Patient(Severity.CRITICAL, 4, 300)
    g.slots[1] = Patient(Severity.MODERATE, 3, 600)
    assert g._start_treatment(0) is True
    assert g._start_treatment(1) is False
    assert g.slots[1].state is PatientState.WAITING


def test_start_treatment_rejects_invalid_slot():
    g = _make_game(42)
    assert g._start_treatment(-1) is False
    assert g._start_treatment(SLOTS) is False
    # empty slot (None)
    assert g._start_treatment(2) is False
    # non-waiting slot
    g.slots[0] = Patient(Severity.MINOR, 1, 1000)
    g.slots[0].state = PatientState.TREATED
    assert g._start_treatment(0) is False
    # WAITING slot succeeds (sanity)
    g.slots[1] = Patient(Severity.MINOR, 1, 1000)
    assert g._start_treatment(1) is True


def test_resolve_treatment_scores_by_severity():
    for sev, expected in [
        (Severity.MINOR, 100),
        (Severity.MODERATE, 200),
        (Severity.CRITICAL, 300),
    ]:
        g = _make_game(42)
        p = Patient(sev, 3, 500)
        g.slots[0] = p
        g._start_treatment(0)
        g.treat_timer = 1
        g._update_treatment()
        assert p.state is PatientState.TREATED
        assert g.score == expected
        assert g.saved_count == 1
        assert g.treating_slot is None


def test_critical_save_recovers_rep():
    g = _make_game(42)
    g.rep = 50
    p = Patient(Severity.CRITICAL, 4, 500)
    g.slots[0] = p
    g._start_treatment(0)
    g.treat_timer = 1
    g._update_treatment()
    assert g.rep == 55


def test_critical_save_rep_capped_at_100():
    g = _make_game(42)
    g.rep = 100
    p = Patient(Severity.CRITICAL, 4, 500)
    g.slots[0] = p
    g._start_treatment(0)
    g.treat_timer = 1
    g._update_treatment()
    assert g.rep == 100


def test_just_in_time_bonus():
    g = _make_game(42)
    p = Patient(Severity.CRITICAL, 4, 50)  # below JUST_IN_TIME=90
    g.slots[0] = p
    g._start_treatment(0)
    g.treat_timer = 1
    g._update_treatment()
    assert g.score == 400  # 300 + 100 bonus
    assert any("JUST IN TIME" in t.text for t in g.floats)


def test_no_just_in_time_bonus_when_early():
    g = _make_game(42)
    p = Patient(Severity.CRITICAL, 4, 300)  # above JUST_IN_TIME=90
    g.slots[0] = p
    g._start_treatment(0)
    g.treat_timer = 1
    g._update_treatment()
    assert g.score == 300


# --- Crash / failure ---


def test_crash_penalties_by_severity():
    for sev, penalty in [(Severity.MINOR, -4), (Severity.MODERATE, -12), (Severity.CRITICAL, -25)]:
        g = _make_game(42)
        g.slots[0] = Patient(sev, 2, 1)
        g._update_patients()
        assert g.slots[0].state is PatientState.CRASHED
        assert g.rep == START_REP + penalty
        assert g.crashed_count == 1


def test_crash_at_exactly_zero_timer():
    g = _make_game(42)
    g.slots[0] = Patient(Severity.CRITICAL, 4, 1)
    g._update_patients()  # 1 -> 0
    assert g.slots[0].state is PatientState.CRASHED


def test_treating_patient_timer_frozen():
    g = _make_game(42)
    p = Patient(Severity.CRITICAL, 4, 5)
    g.slots[0] = p
    g._start_treatment(0)
    timer_before = p.crash_timer
    for _ in range(3):
        g._update_patients()
    assert p.crash_timer == timer_before  # frozen while TREATING
    assert p.state is PatientState.TREATING


def test_waiting_patient_timer_decrements():
    g = _make_game(42)
    p = Patient(Severity.MODERATE, 3, 5)
    g.slots[0] = p
    g._update_patients()
    assert p.crash_timer == 4


def test_rep_floor_zero_and_game_over():
    g = _make_game(42)
    g.rep = 3
    g.slots[0] = Patient(Severity.CRITICAL, 4, 1)
    g._update_patients()
    assert g.rep == 0
    g._check_game_over()
    assert g.phase is Phase.GAME_OVER
    assert g.game_over_reason == "MALPRACTICE"


def test_game_over_at_shift_end():
    g = _make_game(42)
    g.frame = GAME_DURATION - 1
    g._tick()  # frame -> GAME_DURATION
    assert g.phase is Phase.GAME_OVER
    assert g.game_over_reason == "SHIFT OVER"


def test_best_score_persists_on_game_over():
    g = _make_game(42)
    g.score = 500
    g.frame = GAME_DURATION - 1
    g._tick()
    assert g.best_score == 500


# --- Flash cleanup ---


def test_treated_flash_clears_slot():
    g = _make_game(42)
    p = Patient(Severity.MINOR, 1, 1000)
    g.slots[0] = p
    g._start_treatment(0)
    g.treat_timer = 1
    g._update_treatment()
    assert g.slots[0].state is PatientState.TREATED
    assert g.slots[0].flash > 0
    # advance until flash expires
    for _ in range(40):
        g._cleanup_flashes()
    assert g.slots[0] is None


def test_crashed_flash_clears_slot():
    g = _make_game(42)
    g.slots[0] = Patient(Severity.CRITICAL, 4, 1)
    g._update_patients()
    assert g.slots[0].state is PatientState.CRASHED
    for _ in range(40):
        g._cleanup_flashes()
    assert g.slots[0] is None


# --- Slot hit-testing ---


def test_slot_at_hits_center_of_each_card():
    g = _make_game(42)
    for idx in range(SLOTS):
        cx, cy = g._card_center(idx)
        assert g._slot_at(cx, cy) == idx


def test_slot_at_returns_none_outside_cards():
    g = _make_game(42)
    assert g._slot_at(0, 0) is None
    assert g._slot_at(319, 239) is None
    assert g._slot_at(160, 10) is None  # top HUD area
    assert g._slot_at(160, 55) is None  # gap between HUD and row 0


# --- Full tick integration ---


def test_tick_spawns_and_advances():
    g = _make_game(42)
    g.phase = Phase.PLAYING
    g.spawn_timer = 1
    g._tick()
    assert g.frame == 1
    # spawn_timer hit 0 -> spawned -> reset to _spawn_interval()
    assert g.spawn_timer == g._spawn_interval()
    assert any(s is not None for s in g.slots)


def test_particles_spawned_on_resolve():
    g = _make_game(42)
    p = Patient(Severity.CRITICAL, 4, 500)
    g.slots[0] = p
    g._start_treatment(0)
    g.treat_timer = 1
    g._update_treatment()
    # 6 + 3*4 = 18 particles
    assert len(g.particles) == 18


def test_floats_spawned_on_crash():
    g = _make_game(42)
    g.slots[0] = Patient(Severity.CRITICAL, 4, 1)
    g._update_patients()
    assert any("CRASH" in t.text for t in g.floats)


def test_particle_cleanup():
    g = _make_game(42)
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 1, 8)]
    g._update_fx()
    assert len(g.particles) == 0


if __name__ == "__main__":
    import sys

    failures = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
    print(f"\n{failures} failures")
    sys.exit(1 if failures else 0)
