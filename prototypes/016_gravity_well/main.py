"""016_gravity_well — Gravity Well: Orbit & Collapse

Reinterprets game_idea_factory idea #1 (dice/bag roguelite, score 32.2):
- "Log/replay as asset" → resonance echoes from movement trail attract mass
- "Chain collapse" → orbital mass implosion with chain combo scoring
- mana → energy for gravity pulse ability
- heat → risk from too much orbiting mass

Controls:
  WASD/Arrow — move gravity core
  SPACE      — collapse all orbiting mass (chain combo)
  E          — gravity pulse (spend energy, attract all nearby mass instantly)

The most fun moment: building a huge orbital swarm then triggering collapse
for a cascading chain combo score explosion.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
SCREEN_W = 400
SCREEN_H = 300
GRAVITY_RADIUS = 75        # capture radius for mass
ORBIT_RADIUS = 40          # distance mass orbits at
ORBIT_SPEED = 0.04         # radians per frame base orbit speed
PLAYER_SPEED = 2.5
MAX_HEAT = 100
HEAT_PER_MASS = 8          # heat added per orbiting mass
HEAT_DECAY = 0.3           # heat decay per frame when no mass in orbit
COLLAPSE_DURATION = 20     # frames for collapse animation
MAX_ENERGY = 100
ENERGY_REGEN = 0.15        # energy regen per frame
PULSE_COST = 40            # energy cost for gravity pulse
PULSE_RADIUS = 150         # expanded capture radius during pulse
PULSE_DURATION = 10        # frames pulse lasts
RESONANCE_LIFE = 60        # frames resonance echoes persist
RESONANCE_RADIUS = 50      # capture radius for resonance echoes
RESONANCE_INTERVAL = 8     # frames between dropping resonance echoes
MASS_SPAWN_BASE = 45       # base frames between mass spawns
MASS_SPAWN_MIN = 15        # minimum spawn interval
MASS_VALUE_BASE = 10       # base score per mass
PARTICLE_COUNT = 12        # particles per collapsing mass


class Phase(Enum):
    PLAYING = auto()
    COLLAPSING = auto()
    GAME_OVER = auto()


class MassState(Enum):
    DRIFTING = auto()
    ORBITING = auto()
    COLLAPSING = auto()


@dataclass
class MassParticle:
    """A piece of mass that can be captured and collapsed for score."""
    x: float
    y: float
    vx: float
    vy: float
    color: int
    value: int
    state: MassState = MassState.DRIFTING
    orbit_angle: float = 0.0


@dataclass
class ResonanceEcho:
    """A lingering echo from the player's movement trail that attracts mass."""
    x: float
    y: float
    life: int


@dataclass
class CollapseParticle:
    """Visual particle for collapse burst effect."""
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    """Floating score popup."""
    x: float
    y: float
    text: str
    color: int
    life: int


class GravityWell:
    """Main game class: orbital mass capture and chain collapse."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Gravity Well: Orbit & Collapse")
        self.reset()
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        """Reset all game state for a fresh run."""
        # Player
        self.player_x: float = SCREEN_W / 2
        self.player_y: float = SCREEN_H / 2

        # Game state
        self.phase: Phase = Phase.PLAYING
        self.score: int = 0
        self.high_score: int = 0
        self.heat: float = 0.0
        self.energy: float = MAX_ENERGY
        self.chain_multiplier: int = 1
        self.collapse_timer: int = 0
        self.pulse_timer: int = 0
        self.resonance_timer: int = 0
        self.spawn_timer: int = 0
        self.frame_count: int = 0
        self.combo_count: int = 0

        # Entities
        self.masses: list[MassParticle] = []
        self.resonances: list[ResonanceEcho] = []
        self.collapse_particles: list[CollapseParticle] = []
        self.floating_texts: list[FloatingText] = []

    # ── Update ───────────────────────────────────────────────────────────

    def _update(self) -> None:
        """Main update loop."""
        self.frame_count += 1

        if self.phase == Phase.PLAYING:
            self._update_player_input()
            self._update_resonances()
            self._update_mass_capture()
            self._update_mass_movement()
            self._update_spawning()
            self._update_heat()
            self._update_energy()
        elif self.phase == Phase.COLLAPSING:
            self._update_collapse_animation()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_collapse_particles()
        self._update_floating_texts()

    def _update_player_input(self) -> None:
        """Handle player movement and actions."""
        # Movement
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP):
            dy = -1.0
        if pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN):
            dy = 1.0
        if pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT):
            dx = -1.0
        if pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT):
            dx = 1.0

        # Normalize diagonal movement
        mag = math.sqrt(dx * dx + dy * dy)
        if mag > 0:
            dx = (dx / mag) * PLAYER_SPEED
            dy = (dy / mag) * PLAYER_SPEED

        self.player_x += dx
        self.player_y += dy

        # Clamp to screen
        self.player_x = max(10, min(SCREEN_W - 10, self.player_x))
        self.player_y = max(10, min(SCREEN_H - 10, self.player_y))

        # Collapse (SPACE)
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._trigger_collapse()

        # Gravity Pulse (E)
        if pyxel.btnp(pyxel.KEY_E) and self.energy >= PULSE_COST:
            self.energy -= PULSE_COST
            self.pulse_timer = PULSE_DURATION

        # Reset (R on game over)
        if pyxel.btnp(pyxel.KEY_R) and self.phase == Phase.GAME_OVER:
            self.reset()

    def _trigger_collapse(self) -> None:
        """Collapse all orbiting mass for chain combo score."""
        orbiting = [m for m in self.masses if m.state == MassState.ORBITING]
        if not orbiting:
            return

        self.phase = Phase.COLLAPSING
        self.collapse_timer = COLLAPSE_DURATION
        self.chain_multiplier = len(orbiting)
        self.combo_count += 1

        # Calculate score
        total = 0
        for i, mass in enumerate(orbiting):
            mass.state = MassState.COLLAPSING
            # Each mass score = value * (i+1) as chain position multiplier
            points = mass.value * (i + 1)
            total += points
            # Spawn collapse particles
            for _ in range(PARTICLE_COUNT):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(1.0, 4.0)
                self.collapse_particles.append(CollapseParticle(
                    x=mass.x, y=mass.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=mass.color, life=random.randint(10, 25),
                ))
            # Floating score
            self.floating_texts.append(FloatingText(
                x=mass.x, y=mass.y - 5,
                text=str(points), color=mass.color, life=30,
            ))

        self.score += total
        if self.score > self.high_score:
            self.high_score = self.score

        # Combo bonus for consecutive collapses
        if self.combo_count > 1:
            bonus = self.combo_count * 50
            self.score += bonus
            self.floating_texts.append(FloatingText(
                x=self.player_x, y=self.player_y - 20,
                text=f"COMBO x{self.combo_count}!", color=pyxel.COLOR_YELLOW,
                life=40,
            ))

        # Reduce heat after collapse
        self.heat = max(0, self.heat - len(orbiting) * HEAT_PER_MASS * 2)

    def _update_collapse_animation(self) -> None:
        """Update collapse phase — remove collapsed masses."""
        self.collapse_timer -= 1
        if self.collapse_timer <= 0:
            self.masses = [m for m in self.masses
                           if m.state != MassState.COLLAPSING]
            self.phase = Phase.PLAYING

    def _update_resonances(self) -> None:
        """Drop resonance echoes along player's movement path."""
        self.resonance_timer += 1
        if self.resonance_timer >= RESONANCE_INTERVAL:
            self.resonance_timer = 0
            self.resonances.append(ResonanceEcho(
                x=self.player_x, y=self.player_y,
                life=RESONANCE_LIFE,
            ))

        for r in self.resonances:
            r.life -= 1
        self.resonances = [r for r in self.resonances if r.life > 0]

    def _update_mass_capture(self) -> None:
        """Check if drifting mass is within capture radius and pull into orbit."""
        effective_radius = PULSE_RADIUS if self.pulse_timer > 0 else GRAVITY_RADIUS

        for mass in self.masses:
            if mass.state != MassState.DRIFTING:
                continue
            # Player gravity
            dx = mass.x - self.player_x
            dy = mass.y - self.player_y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < effective_radius and dist > 0:
                pull = (effective_radius - dist) / effective_radius * 0.3
                mass.vx -= (dx / dist) * pull
                mass.vy -= (dy / dist) * pull

                if dist < ORBIT_RADIUS + 5:
                    mass.state = MassState.ORBITING
                    mass.orbit_angle = math.atan2(dy, dx)
                    mass.x = self.player_x + math.cos(mass.orbit_angle) * ORBIT_RADIUS
                    mass.y = self.player_y + math.sin(mass.orbit_angle) * ORBIT_RADIUS

            # Resonance echoes gravity
            for r in self.resonances:
                rdx = mass.x - r.x
                rdy = mass.y - r.y
                rdist = math.sqrt(rdx * rdx + rdy * rdy)
                if rdist < RESONANCE_RADIUS and rdist > 0:
                    rpull = (RESONANCE_RADIUS - rdist) / RESONANCE_RADIUS * 0.15
                    mass.vx -= (rdx / rdist) * rpull
                    mass.vy -= (rdy / rdist) * rpull

    def _update_mass_movement(self) -> None:
        """Move mass particles and update orbits."""
        for mass in self.masses:
            if mass.state == MassState.DRIFTING:
                mass.vx *= 0.995
                mass.vy *= 0.995
                mass.x += mass.vx
                mass.y += mass.vy
                if mass.x < 0:
                    mass.x = 0
                    mass.vx = abs(mass.vx)
                elif mass.x > SCREEN_W:
                    mass.x = SCREEN_W
                    mass.vx = -abs(mass.vx)
                if mass.y < 0:
                    mass.y = 0
                    mass.vy = abs(mass.vy)
                elif mass.y > SCREEN_H:
                    mass.y = SCREEN_H
                    mass.vy = -abs(mass.vy)
            elif mass.state == MassState.ORBITING:
                mass.orbit_angle += ORBIT_SPEED * (1.0 + random.uniform(-0.01, 0.01))
                wobble = ORBIT_RADIUS + random.uniform(-2, 2)
                mass.x = self.player_x + math.cos(mass.orbit_angle) * wobble
                mass.y = self.player_y + math.sin(mass.orbit_angle) * wobble

        self.masses = [
            m for m in self.masses
            if m.state != MassState.DRIFTING
            or (-50 < m.x < SCREEN_W + 50 and -50 < m.y < SCREEN_H + 50)
        ]

    def _update_spawning(self) -> None:
        """Spawn new mass particles from edges."""
        self.spawn_timer += 1
        interval = max(MASS_SPAWN_MIN,
                       MASS_SPAWN_BASE - self.frame_count // 600)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            self._spawn_mass()

    def _spawn_mass(self) -> None:
        """Spawn a single mass particle from a random edge."""
        edge = random.randint(0, 3)
        colors = [pyxel.COLOR_RED, pyxel.COLOR_GREEN, pyxel.COLOR_CYAN,
                  pyxel.COLOR_ORANGE, pyxel.COLOR_PINK, pyxel.COLOR_LIME,
                  pyxel.COLOR_YELLOW, pyxel.COLOR_PURPLE]
        if edge == 0:  # top
            x = random.uniform(0, SCREEN_W)
            y = -5.0
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(0.2, 1.0)
        elif edge == 1:  # right
            x = SCREEN_W + 5.0
            y = random.uniform(0, SCREEN_H)
            vx = random.uniform(-1.0, -0.2)
            vy = random.uniform(-0.5, 0.5)
        elif edge == 2:  # bottom
            x = random.uniform(0, SCREEN_W)
            y = SCREEN_H + 5.0
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-1.0, -0.2)
        else:  # left
            x = -5.0
            y = random.uniform(0, SCREEN_H)
            vx = random.uniform(0.2, 1.0)
            vy = random.uniform(-0.5, 0.5)

        color = random.choice(colors)
        value = MASS_VALUE_BASE + random.randint(0, 20)
        self.masses.append(MassParticle(x=x, y=y, vx=vx, vy=vy,
                                        color=color, value=value))

    def _update_heat(self) -> None:
        """Update heat: +heat for orbiting mass, decay when empty."""
        orbiting_count = sum(1 for m in self.masses
                             if m.state == MassState.ORBITING)
        self.heat += orbiting_count * HEAT_PER_MASS * 0.05
        if orbiting_count == 0:
            self.heat = max(0, self.heat - HEAT_DECAY)
        self.heat = min(MAX_HEAT, self.heat)

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _update_energy(self) -> None:
        """Regenerate energy over time."""
        self.energy = min(MAX_ENERGY, self.energy + ENERGY_REGEN)
        if self.pulse_timer > 0:
            self.pulse_timer -= 1

    def _update_game_over(self) -> None:
        """Handle game over state."""
        pass

    def _update_collapse_particles(self) -> None:
        """Update collapse visual particles."""
        for p in self.collapse_particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.95
            p.vy *= 0.95
            p.life -= 1
        self.collapse_particles = [p for p in self.collapse_particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        """Update floating score texts."""
        for t in self.floating_texts:
            t.y -= 0.8
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    # ── Draw ─────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(pyxel.COLOR_BLACK)

        self._draw_stars()
        self._draw_resonances()
        self._draw_masses()
        self._draw_player()
        self._draw_collapse_particles()
        self._draw_floating_texts()
        self._draw_ui()

    def _draw_stars(self) -> None:
        """Draw subtle background stars (deterministic from seed)."""
        state = random.getstate()
        random.seed(42)
        for i in range(40):
            sx = (i * 97 + 13) % SCREEN_W
            sy = (i * 73 + 29) % SCREEN_H
            brightness = (self.frame_count // 4 + i) % 3
            if brightness == 0:
                pyxel.pset(sx, sy, pyxel.COLOR_NAVY)
        random.setstate(state)

    def _draw_resonances(self) -> None:
        """Draw resonance echoes as fading dots."""
        for r in self.resonances:
            alpha_ratio = r.life / RESONANCE_LIFE
            if alpha_ratio > 0.5:
                col = pyxel.COLOR_LIGHT_BLUE
            elif alpha_ratio > 0.2:
                col = pyxel.COLOR_NAVY
            else:
                continue
            pyxel.circb(int(r.x), int(r.y), 3, col)

    def _draw_masses(self) -> None:
        """Draw all mass particles."""
        for mass in self.masses:
            if mass.state == MassState.DRIFTING:
                pyxel.rect(int(mass.x) - 2, int(mass.y) - 2, 4, 4, mass.color)
            elif mass.state == MassState.ORBITING:
                pyxel.rect(int(mass.x) - 3, int(mass.y) - 3, 6, 6, mass.color)
                pyxel.line(int(self.player_x), int(self.player_y),
                           int(mass.x), int(mass.y),
                           pyxel.COLOR_NAVY)
            elif mass.state == MassState.COLLAPSING:
                shrink = self.collapse_timer / COLLAPSE_DURATION
                size = int(4 * shrink)
                if size > 0:
                    pyxel.rect(int(mass.x) - size // 2, int(mass.y) - size // 2,
                               size, size, mass.color)

    def _draw_player(self) -> None:
        """Draw the gravity core player."""
        effective_radius = PULSE_RADIUS if self.pulse_timer > 0 else GRAVITY_RADIUS
        if self.pulse_timer > 0:
            pulse_col = (
                pyxel.COLOR_CYAN
                if (self.frame_count // 2) % 2 == 0
                else pyxel.COLOR_LIGHT_BLUE
            )
            pyxel.circb(int(self.player_x), int(self.player_y),
                        effective_radius, pulse_col)
        else:
            pyxel.circb(int(self.player_x), int(self.player_y),
                        effective_radius, pyxel.COLOR_NAVY)

        pyxel.circb(int(self.player_x), int(self.player_y),
                    ORBIT_RADIUS, pyxel.COLOR_DARK_BLUE)

        core_col = pyxel.COLOR_WHITE
        if self.phase == Phase.COLLAPSING:
            core_col = pyxel.COLOR_ORANGE
        elif self.heat > MAX_HEAT * 0.7:
            core_col = pyxel.COLOR_RED
        pyxel.circ(int(self.player_x), int(self.player_y), 4, core_col)
        pyxel.circ(int(self.player_x), int(self.player_y), 2, pyxel.COLOR_BLACK)

    def _draw_collapse_particles(self) -> None:
        """Draw collapse burst particles."""
        for p in self.collapse_particles:
            alpha = p.life / 25
            col = p.color if alpha > 0.3 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        """Draw floating score popups."""
        for t in self.floating_texts:
            alpha = t.life / 40
            col = t.color if alpha > 0.3 else pyxel.COLOR_GRAY
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, col)

    def _draw_ui(self) -> None:
        """Draw HUD: score, heat bar, energy bar, instructions."""
        # Score
        pyxel.text(5, 4, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)
        pyxel.text(5, 12, f"HI:{self.high_score:06d}", pyxel.COLOR_GRAY)

        # Heat bar
        bar_x, bar_y = 5, 22
        bar_w, bar_h = 80, 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_NAVY)
        heat_w = int(bar_w * (self.heat / MAX_HEAT))
        heat_col = pyxel.COLOR_RED if self.heat > MAX_HEAT * 0.7 else pyxel.COLOR_ORANGE
        if heat_w > 0:
            pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_col)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", pyxel.COLOR_GRAY)

        # Energy bar
        ebar_y = 31
        pyxel.rect(bar_x, ebar_y, bar_w, bar_h, pyxel.COLOR_NAVY)
        energy_w = int(bar_w * (self.energy / MAX_ENERGY))
        if energy_w > 0:
            pyxel.rect(bar_x, ebar_y, energy_w, bar_h, pyxel.COLOR_CYAN)
        pyxel.text(bar_x + bar_w + 4, ebar_y - 1, "NRG", pyxel.COLOR_GRAY)

        # Orbiting mass count
        orbiting = sum(1 for m in self.masses if m.state == MassState.ORBITING)
        pyxel.text(5, 41, f"ORBIT:{orbiting}", pyxel.COLOR_WHITE)

        # Chain multiplier display during collapse
        if self.phase == Phase.COLLAPSING:
            chain_text = f"CHAIN x{self.chain_multiplier}!"
            tx = SCREEN_W // 2 - len(chain_text) * 2
            pyxel.text(tx, SCREEN_H // 3, chain_text,
                       pyxel.COLOR_YELLOW
                       if (self.frame_count // 4) % 2 == 0
                       else pyxel.COLOR_ORANGE)

        # Combo display
        if self.combo_count > 1 and self.phase == Phase.PLAYING:
            combo_text = f"Combo: x{self.combo_count}"
            pyxel.text(SCREEN_W - len(combo_text) * 4 - 5, 4, combo_text,
                       pyxel.COLOR_YELLOW)

        # Instructions
        if self.phase == Phase.PLAYING:
            pyxel.text(5, SCREEN_H - 10, "WASD:Move SPACE:Collapse E:Pulse",
                       pyxel.COLOR_GRAY)
        elif self.phase == Phase.GAME_OVER:
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2, "GAME OVER",
                       pyxel.COLOR_RED)
            pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 12,
                       f"SCORE: {self.score}", pyxel.COLOR_WHITE)
            pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 + 22,
                       "Press R to restart", pyxel.COLOR_GRAY)

        # Pulse cooldown indicator
        if self.energy < PULSE_COST:
            cd_text = f"PULSE:{int(self.energy)}/{PULSE_COST}"
            pyxel.text(5, SCREEN_H - 20, cd_text, pyxel.COLOR_NAVY)


if __name__ == "__main__":
    GravityWell()
