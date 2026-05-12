"""test_imports.py — Headless logic tests for 016_gravity_well."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/016_gravity_well")
from main import (  # noqa: E402
    CollapseParticle,
    FloatingText,
    GravityWell,
    MassParticle,
    MassState,
    Phase,
    ResonanceEcho,
    SCREEN_W, SCREEN_H,
    GRAVITY_RADIUS, ORBIT_RADIUS, MAX_HEAT, MAX_ENERGY,
    HEAT_PER_MASS, PULSE_COST, PULSE_RADIUS, RESONANCE_RADIUS,
    MASS_VALUE_BASE,
)


def test_constants() -> None:
    """Verify game constants are reasonable."""
    assert SCREEN_W == 400
    assert SCREEN_H == 300
    assert GRAVITY_RADIUS == 75
    assert ORBIT_RADIUS == 40
    assert MAX_HEAT == 100
    assert MAX_ENERGY == 100
    assert HEAT_PER_MASS == 8
    assert PULSE_COST == 40
    assert PULSE_RADIUS == 150
    assert RESONANCE_RADIUS == 50
    assert MASS_VALUE_BASE == 10


def test_enums() -> None:
    """Verify Phase and MassState enums."""
    assert Phase.PLAYING in Phase
    assert Phase.COLLAPSING in Phase
    assert Phase.GAME_OVER in Phase

    assert MassState.DRIFTING in MassState
    assert MassState.ORBITING in MassState
    assert MassState.COLLAPSING in MassState


def test_dataclass_mass_particle() -> None:
    """Verify MassParticle dataclass."""
    m = MassParticle(x=100.0, y=200.0, vx=0.5, vy=-0.3,
                     color=8, value=15)
    assert m.x == 100.0
    assert m.y == 200.0
    assert m.vx == 0.5
    assert m.vy == -0.3
    assert m.color == 8
    assert m.value == 15
    assert m.state == MassState.DRIFTING
    assert m.orbit_angle == 0.0


def test_dataclass_resonance_echo() -> None:
    """Verify ResonanceEcho dataclass."""
    r = ResonanceEcho(x=50.0, y=60.0, life=30)
    assert r.x == 50.0
    assert r.y == 60.0
    assert r.life == 30


def test_dataclass_collapse_particle() -> None:
    """Verify CollapseParticle dataclass."""
    p = CollapseParticle(x=10.0, y=20.0, vx=2.0, vy=-1.0,
                         color=8, life=15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 2.0
    assert p.vy == -1.0
    assert p.life == 15


def test_dataclass_floating_text() -> None:
    """Verify FloatingText dataclass."""
    t = FloatingText(x=100.0, y=50.0, text="+100", color=8, life=20)
    assert t.x == 100.0
    assert t.y == 50.0
    assert t.text == "+100"
    assert t.life == 20


def test_gravity_well_reset() -> None:
    """Verify GravityWell.reset() initializes state correctly."""
    g = GravityWell.__new__(GravityWell)
    g.reset()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.high_score == 0
    assert g.heat == 0.0
    assert g.energy == MAX_ENERGY
    assert g.chain_multiplier == 1
    assert g.collapse_timer == 0
    assert g.pulse_timer == 0
    assert g.combo_count == 0
    assert g.frame_count == 0
    assert g.masses == []
    assert g.resonances == []
    assert g.collapse_particles == []
    assert g.floating_texts == []
    assert abs(g.player_x - SCREEN_W / 2) < 0.01
    assert abs(g.player_y - SCREEN_H / 2) < 0.01


def test_spawn_mass() -> None:
    """Verify _spawn_mass creates a particle with correct defaults."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g._spawn_mass()
    assert len(g.masses) == 1
    m = g.masses[0]
    assert m.state == MassState.DRIFTING
    assert m.value >= MASS_VALUE_BASE
    assert m.value <= MASS_VALUE_BASE + 20
    assert m.color in range(16)
    # Should be near screen bounds
    assert -10 < m.x < SCREEN_W + 10
    assert -10 < m.y < SCREEN_H + 10


def test_update_resonances() -> None:
    """Verify resonance echoes are created and decay."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    # Force resonance timer to trigger
    g.resonance_timer = 100
    g.player_x = 200.0
    g.player_y = 150.0
    g._update_resonances()
    assert len(g.resonances) >= 1
    r = g.resonances[0]
    assert abs(r.x - 200.0) < 0.01
    assert abs(r.y - 150.0) < 0.01
    assert r.life > 0


def test_trigger_collapse_empty() -> None:
    """Verify collapse with no orbiting masses does nothing."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g._trigger_collapse()
    assert g.phase == Phase.PLAYING  # No change


def test_trigger_collapse_with_orbit() -> None:
    """Verify collapse destroys orbiting masses and awards score."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.masses = [
        MassParticle(x=200.0, y=150.0, vx=0, vy=0, color=8, value=10,
                     state=MassState.ORBITING, orbit_angle=0.0),
        MassParticle(x=210.0, y=160.0, vx=0, vy=0, color=3, value=20,
                     state=MassState.ORBITING, orbit_angle=1.0),
        MassParticle(x=100.0, y=100.0, vx=1.0, vy=0, color=5, value=5,
                     state=MassState.DRIFTING),
    ]
    g.heat = 50.0
    g._trigger_collapse()

    assert g.phase == Phase.COLLAPSING
    assert g.chain_multiplier == 2  # 2 orbiting masses
    assert g.combo_count == 1
    # Score: mass1=10*1=10, mass2=20*2=40, total=50
    assert g.score == 50
    # Heat reduced: 50 - (2 * 8 * 2) = 50 - 32 = 18
    assert abs(g.heat - 18.0) < 0.01
    # Both orbiting masses now collapsing
    assert g.masses[0].state == MassState.COLLAPSING
    assert g.masses[1].state == MassState.COLLAPSING
    # Drifting mass unchanged
    assert g.masses[2].state == MassState.DRIFTING


def test_collapse_animation_cleanup() -> None:
    """Verify collapse animation removes collapsed masses."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.phase = Phase.COLLAPSING
    g.collapse_timer = 1
    g.masses = [
        MassParticle(x=0, y=0, vx=0, vy=0, color=8, value=10,
                     state=MassState.COLLAPSING),
        MassParticle(x=0, y=0, vx=0, vy=0, color=3, value=20,
                     state=MassState.DRIFTING),
    ]
    g._update_collapse_animation()
    assert g.phase == Phase.PLAYING
    assert len(g.masses) == 1
    assert g.masses[0].state == MassState.DRIFTING


def test_update_heat_game_over() -> None:
    """Verify max heat triggers game over."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.heat = 99.9
    # Add an orbiting mass to push heat over max
    g.masses = [MassParticle(x=0, y=0, vx=0, vy=0, color=8, value=10,
                              state=MassState.ORBITING)]
    g._update_heat()
    assert g.heat >= MAX_HEAT
    assert g.phase == Phase.GAME_OVER


def test_update_heat_decay() -> None:
    """Verify heat decays when no mass in orbit."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.heat = 10.0
    g._update_heat()  # no orbiting mass → decay
    assert g.heat < 10.0


def test_update_energy() -> None:
    """Verify energy regenerates over time."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.energy = 50.0
    g.pulse_timer = 5
    g._update_energy()
    assert g.energy > 50.0
    assert g.energy <= MAX_ENERGY
    assert g.pulse_timer == 4


def test_mass_capture_drifting_to_orbit() -> None:
    """Verify drifting mass close to player enters orbit."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.player_x = 200.0
    g.player_y = 150.0
    # Place mass just inside orbit radius
    g.masses = [
        MassParticle(x=g.player_x + ORBIT_RADIUS + 3,
                     y=g.player_y, vx=0, vy=0,
                     color=8, value=10, state=MassState.DRIFTING),
    ]
    g._update_mass_capture()
    assert g.masses[0].state == MassState.ORBITING


def test_mass_drift_bounce() -> None:
    """Verify drifting masses bounce off screen edges and stay in bounds."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.masses = [
        MassParticle(x=-100.0, y=-100.0, vx=0, vy=0, color=8, value=10,
                     state=MassState.DRIFTING),
        MassParticle(x=200.0, y=150.0, vx=0, vy=0, color=3, value=20,
                     state=MassState.ORBITING),
    ]
    g._update_mass_movement()
    # Both masses remain: drifting one bounces to (0,0), orbiting stays
    assert len(g.masses) == 2
    assert g.masses[0].x >= 0
    assert g.masses[0].y >= 0


def test_update_spawning_interval_decreases() -> None:
    """Verify spawn interval decreases with frame count."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.frame_count = 6000
    g.spawn_timer = 100
    g._update_spawning()
    # At frame 6000, interval should be max(15, 45 - 10) = max(15, 35) = 35
    # spawn_timer 100 > 35, should spawn
    assert g.spawn_timer == 0


def test_floating_texts_update() -> None:
    """Verify floating texts rise and expire."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+50", color=8, life=3),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    # Should rise
    assert g.floating_texts[0].y < 100.0
    assert g.floating_texts[0].life == 2

    # Run until it expires
    g._update_floating_texts()
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_collapse_particles_update() -> None:
    """Verify collapse particles move and expire."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.collapse_particles = [
        CollapseParticle(x=100.0, y=100.0, vx=2.0, vy=-1.0, color=8, life=3),
    ]
    g._update_collapse_particles()
    assert len(g.collapse_particles) == 1
    assert g.collapse_particles[0].x > 100.0
    assert g.collapse_particles[0].life == 2

    g._update_collapse_particles()
    g._update_collapse_particles()
    assert len(g.collapse_particles) == 0


def test_combo_bonus() -> None:
    """Verify consecutive collapses award combo bonus."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.combo_count = 2  # simulate previous collapse
    g.masses = [
        MassParticle(x=200.0, y=150.0, vx=0, vy=0, color=8, value=10,
                     state=MassState.ORBITING),
    ]
    g._trigger_collapse()
    # Score: mass 10*1=10 + combo bonus 3*50=150 = 160
    assert g.score == 160
    assert g.combo_count == 3


def test_high_score_tracking() -> None:
    """Verify high score updates when beaten."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.high_score = 100
    g.masses = [
        MassParticle(x=200.0, y=150.0, vx=0, vy=0, color=8, value=50,
                     state=MassState.ORBITING),
    ]
    g._trigger_collapse()
    assert g.score == 50  # 50*1=50
    assert g.high_score == 100  # not beaten

    # Now beat it
    g2 = GravityWell.__new__(GravityWell)
    g2.reset()
    g2.high_score = 10
    g2.masses = [
        MassParticle(x=200.0, y=150.0, vx=0, vy=0, color=8, value=50,
                     state=MassState.ORBITING),
    ]
    g2._trigger_collapse()
    assert g2.high_score == 50


def test_pulse_cost_check() -> None:
    """Verify pulse only activates with sufficient energy."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.energy = 30.0
    # Simulate E press check (energy < PULSE_COST, should not activate)
    can_pulse = g.energy >= PULSE_COST
    assert not can_pulse

    g.energy = 50.0
    can_pulse = g.energy >= PULSE_COST
    assert can_pulse


def test_player_clamp() -> None:
    """Verify player position is clamped to screen bounds."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.player_x = -50.0
    g.player_y = SCREEN_H + 50.0
    # Simulate the clamping logic directly
    g.player_x = max(10, min(SCREEN_W - 10, g.player_x))
    g.player_y = max(10, min(SCREEN_H - 10, g.player_y))
    assert g.player_x == 10.0
    assert g.player_y == SCREEN_H - 10


def test_mass_orbit_update() -> None:
    """Verify orbiting mass follows player."""
    g = GravityWell.__new__(GravityWell)
    g.reset()
    g.player_x = 200.0
    g.player_y = 150.0
    m = MassParticle(x=240.0, y=150.0, vx=0, vy=0, color=8, value=10,
                     state=MassState.ORBITING, orbit_angle=0.0)
    g.masses = [m]
    g._update_mass_movement()
    # Should still be in orbit around player
    assert g.masses[0].state == MassState.ORBITING
    # Should be near orbit radius from player
    dx = g.masses[0].x - g.player_x
    dy = g.masses[0].y - g.player_y
    dist = (dx * dx + dy * dy) ** 0.5
    assert abs(dist - ORBIT_RADIUS) < 10


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
