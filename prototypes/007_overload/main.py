"""OVERLOAD — Power Core Survival Auto-Shooter.

A Vampire Survivors-like auto-shooter where you control a power core.
Manage your charge meter: high charge boosts fire rate, but you can
trigger OVERLOAD to clear the screen at the cost of HP. Chain reactions
propagate between nearby enemies.

Core mechanic: "Unleashing a chain-reaction overload that cascades
through every enemy on screen is the most satisfying moment."

Controls:
    Arrow keys / WASD — move
    SPACE — trigger OVERLOAD (when charge >= 100)
    R — restart on game over
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ── Config ──────────────────────────────────────────────────────────────────

SCREEN_W = 400
SCREEN_H = 300
DISPLAY_SCALE = 2
FPS = 60

PLAYER_SPEED = 2.0
PLAYER_RADIUS = 8
PLAYER_MAX_HP = 100
PLAYER_COLLECT_RANGE = 40.0

AUTO_FIRE_INTERVAL = 30  # frames between shots at 0 charge
AUTO_FIRE_MIN_INTERVAL = 12  # minimum interval at 100 charge
BULLET_SPEED = 5.0
BULLET_DAMAGE = 8
BULLET_RADIUS = 3

ENEMY_BASE_SPEED = 0.8
ENEMY_BASE_HP = 20
ENEMY_RADIUS = 6
ENEMY_SPAWN_INTERVAL = 45  # frames between spawns initially
ENEMY_SPAWN_MIN = 12  # minimum spawn interval
ENEMY_DAMAGE = 8  # contact damage per frame

ORB_VALUE_MIN = 5
ORB_VALUE_MAX = 10
ORB_LIFETIME = 300  # frames before orb disappears

CHARGE_MAX = 100
OVERLOAD_BASE_DAMAGE = 50  # base damage of overload
OVERLOAD_HP_COST = 15  # HP cost to trigger overload
OVERLOAD_CHAIN_RANGE = 60.0  # px range for chain propagation
OVERLOAD_CHAIN_FALLOFF = 0.5  # damage multiplier per chain step

WAVE_DURATION = 30 * FPS  # 30 seconds per wave
WAVE_SPAWN_BOOST = 5  # spawn interval reduction per wave

PARTICLE_COUNT_SMALL = 5
PARTICLE_COUNT_LARGE = 15


# ── Enums ───────────────────────────────────────────────────────────────────

class Phase(Enum):
    PLAYING = auto()
    OVERLOAD_ANIM = auto()
    GAME_OVER = auto()


# ── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class Player:
    x: float
    y: float
    hp: int = PLAYER_MAX_HP
    charge: float = 0.0
    fire_cooldown: int = 0


@dataclass
class Enemy:
    x: float
    y: float
    hp: int
    speed: float
    radius: int = ENEMY_RADIUS


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    damage: int = BULLET_DAMAGE


@dataclass
class EnergyOrb:
    x: float
    y: float
    value: int
    life: int = ORB_LIFETIME


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


# ── Game ────────────────────────────────────────────────────────────────────

class Game:
    """Main game class for OVERLOAD."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="OVERLOAD", display_scale=DISPLAY_SCALE, fps=FPS)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all game state for a new run."""
        self.player = Player(x=SCREEN_W / 2, y=SCREEN_H / 2)
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.orbs: list[EnergyOrb] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.phase = Phase.PLAYING
        self.score: int = 0
        self.wave: int = 1
        self.spawn_timer: int = 0
        self.wave_timer: int = 0
        self.shake_timer: int = 0
        self.overload_anim_timer: int = 0

    # ── Update ──────────────────────────────────────────────────────────────

    def update(self) -> None:
        """Main update loop — dispatch by phase."""
        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.OVERLOAD_ANIM:
            self._update_overload_anim()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_playing(self) -> None:
        """Update logic during active gameplay."""
        # Input
        if pyxel.btn(pyxel.KEY_R):
            self.reset()
            return

        self._handle_movement()
        self._handle_overload_trigger()
        self._update_fire()
        self._update_bullets()
        self._spawn_enemies()
        self._update_enemies()
        self._check_collisions()
        self._update_orbs()
        self._collect_orbs()
        self._update_particles()
        self._update_floating_texts()
        self._update_wave()

        if self.shake_timer > 0:
            self.shake_timer -= 1

        # Check death
        if self.player.hp <= 0:
            self.player.hp = 0
            self.phase = Phase.GAME_OVER

    def _handle_movement(self) -> None:
        """Handle player movement with arrow keys and WASD."""
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += 1.0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= 1.0
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += 1.0

        # Normalize diagonal movement
        if dx != 0.0 and dy != 0.0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv

        self.player.x += dx * PLAYER_SPEED
        self.player.y += dy * PLAYER_SPEED

        # Clamp to screen
        self.player.x = max(PLAYER_RADIUS, min(SCREEN_W - PLAYER_RADIUS, self.player.x))
        self.player.y = max(PLAYER_RADIUS, min(SCREEN_H - PLAYER_RADIUS, self.player.y))

    def _handle_overload_trigger(self) -> None:
        """Check if player triggers OVERLOAD."""
        if pyxel.btnp(pyxel.KEY_SPACE) and self.player.charge >= CHARGE_MAX:
            self._trigger_overload()

    def _trigger_overload(self) -> None:
        """Execute OVERLOAD: damage all enemies with chain reactions, cost HP."""
        self.player.hp -= OVERLOAD_HP_COST
        self.player.charge = 0.0
        self.phase = Phase.OVERLOAD_ANIM
        self.overload_anim_timer = 30  # half-second animation
        self.shake_timer = 15

        # Calculate overload damage (scales slightly with wave)
        base_dmg = OVERLOAD_BASE_DAMAGE + self.wave * 5

        # Track which enemies get damaged and at what multiplier
        damaged: dict[int, float] = {}  # enemy index -> damage multiplier

        # Initial overload hits ALL enemies
        for i, enemy in enumerate(self.enemies):
            damaged[i] = 1.0

        # Chain propagation: enemies killed by overload propagate damage
        # Simulate chains iteratively
        chain_sources = list(range(len(self.enemies)))
        current_multiplier = 1.0

        while chain_sources and current_multiplier > 0.05:
            next_sources: list[int] = []
            next_multiplier = current_multiplier * OVERLOAD_CHAIN_FALLOFF
            for src_idx in chain_sources:
                src = self.enemies[src_idx]
                # Check if this source would be killed
                src_dmg = base_dmg * damaged.get(src_idx, 0.0)
                if src_dmg < src.hp:
                    continue  # not killed, no chain
                # Propagate to nearby un-damaged enemies
                for j, enemy in enumerate(self.enemies):
                    if j in damaged:
                        continue
                    dist = math.hypot(src.x - enemy.x, src.y - enemy.y)
                    if dist <= OVERLOAD_CHAIN_RANGE:
                        damaged[j] = next_multiplier
                        next_sources.append(j)
            chain_sources = next_sources
            current_multiplier = next_multiplier

        # Apply damage and spawn effects
        for i, mult in damaged.items():
            dmg = base_dmg * mult
            enemy = self.enemies[i]
            enemy.hp -= int(dmg)
            self._spawn_particles(enemy.x, enemy.y, PARTICLE_COUNT_SMALL, pyxel.COLOR_YELLOW)
            if enemy.hp <= 0:
                self._spawn_particles(enemy.x, enemy.y, PARTICLE_COUNT_LARGE, pyxel.COLOR_ORANGE)
                self._spawn_floating_text(enemy.x, enemy.y, f"{int(dmg)}", pyxel.COLOR_YELLOW)
                self.score += 10 * self.wave

        # Remove dead enemies and drop orbs
        self._cleanup_dead_enemies()

    def _update_fire(self) -> None:
        """Auto-fire bullets at nearest enemy."""
        if self.player.fire_cooldown > 0:
            self.player.fire_cooldown -= 1
            return

        # Find nearest enemy
        if not self.enemies:
            return

        nearest = min(
            self.enemies,
            key=lambda e: math.hypot(self.player.x - e.x, self.player.y - e.y),
        )
        dist = math.hypot(self.player.x - nearest.x, self.player.y - nearest.y)
        if dist < 1.0:
            return

        dx = (nearest.x - self.player.x) / dist
        dy = (nearest.y - self.player.y) / dist

        self.bullets.append(
            Bullet(
                x=self.player.x,
                y=self.player.y,
                vx=dx * BULLET_SPEED,
                vy=dy * BULLET_SPEED,
            )
        )

        # Fire rate scales with charge
        charge_ratio = self.player.charge / CHARGE_MAX
        interval = AUTO_FIRE_INTERVAL - int(
            (AUTO_FIRE_INTERVAL - AUTO_FIRE_MIN_INTERVAL) * charge_ratio
        )
        self.player.fire_cooldown = max(AUTO_FIRE_MIN_INTERVAL, interval)

    def _update_bullets(self) -> None:
        """Move bullets and check for off-screen / hit enemies."""
        alive: list[Bullet] = []
        for b in self.bullets:
            b.x += b.vx
            b.y += b.vy
            # Check bounds
            if b.x < 0 or b.x > SCREEN_W or b.y < 0 or b.y > SCREEN_H:
                continue
            # Check hit
            hit = False
            for enemy in self.enemies:
                if math.hypot(b.x - enemy.x, b.y - enemy.y) < enemy.radius + BULLET_RADIUS:
                    enemy.hp -= b.damage
                    self._spawn_particles(b.x, b.y, 3, pyxel.COLOR_WHITE)
                    if enemy.hp <= 0:
                        self._spawn_particles(enemy.x, enemy.y, PARTICLE_COUNT_SMALL, pyxel.COLOR_RED)
                        self._spawn_floating_text(enemy.x, enemy.y, f"{b.damage}", pyxel.COLOR_WHITE)
                        self.score += 1 * self.wave
                        self._drop_orb(enemy.x, enemy.y)
                    hit = True
                    break
            if not hit:
                alive.append(b)
        self.bullets = alive
        self._cleanup_dead_enemies()

    def _spawn_enemies(self) -> None:
        """Spawn enemies from screen edges with wave-based scaling."""
        self.spawn_timer -= 1
        if self.spawn_timer > 0:
            return

        # Spawn interval decreases per wave
        interval = max(ENEMY_SPAWN_MIN, ENEMY_SPAWN_INTERVAL - self.wave * WAVE_SPAWN_BOOST)
        self.spawn_timer = interval

        # Pick a random edge
        edge = random.randint(0, 3)
        if edge == 0:  # top
            x = random.uniform(0, SCREEN_W)
            y = -ENEMY_RADIUS
        elif edge == 1:  # right
            x = SCREEN_W + ENEMY_RADIUS
            y = random.uniform(0, SCREEN_H)
        elif edge == 2:  # bottom
            x = random.uniform(0, SCREEN_W)
            y = SCREEN_H + ENEMY_RADIUS
        else:  # left
            x = -ENEMY_RADIUS
            y = random.uniform(0, SCREEN_H)

        # Enemy stats scale with wave
        hp = ENEMY_BASE_HP + self.wave * 5
        speed = ENEMY_BASE_SPEED + self.wave * 0.1

        self.enemies.append(Enemy(x=x, y=y, hp=hp, speed=speed))

    def _update_enemies(self) -> None:
        """Move enemies toward player."""
        for enemy in self.enemies:
            dx = self.player.x - enemy.x
            dy = self.player.y - enemy.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                enemy.x += (dx / dist) * enemy.speed
                enemy.y += (dy / dist) * enemy.speed

    def _check_collisions(self) -> None:
        """Check player-enemy collisions (contact damage)."""
        for enemy in self.enemies:
            if math.hypot(self.player.x - enemy.x, self.player.y - enemy.y) < PLAYER_RADIUS + enemy.radius:
                self.player.hp -= ENEMY_DAMAGE
                self.shake_timer = max(self.shake_timer, 3)
                self._spawn_particles(
                    (self.player.x + enemy.x) / 2,
                    (self.player.y + enemy.y) / 2,
                    2,
                    pyxel.COLOR_RED,
                )

    def _update_orbs(self) -> None:
        """Update orb lifetimes."""
        for orb in self.orbs:
            orb.life -= 1
        self.orbs = [o for o in self.orbs if o.life > 0]

    def _collect_orbs(self) -> None:
        """Player collects nearby energy orbs."""
        remaining: list[EnergyOrb] = []
        for orb in self.orbs:
            dist = math.hypot(self.player.x - orb.x, self.player.y - orb.y)
            if dist <= PLAYER_COLLECT_RANGE:
                self.player.charge = min(CHARGE_MAX, self.player.charge + orb.value)
                self._spawn_floating_text(orb.x, orb.y, f"+{orb.value}", pyxel.COLOR_CYAN)
            else:
                remaining.append(orb)
        self.orbs = remaining

    def _drop_orb(self, x: float, y: float) -> None:
        """Spawn an energy orb at enemy death location."""
        value = random.randint(ORB_VALUE_MIN, ORB_VALUE_MAX)
        self.orbs.append(EnergyOrb(x=x, y=y, value=value))

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        """Update floating text positions and lifetimes."""
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_wave(self) -> None:
        """Advance wave timer and increase difficulty."""
        self.wave_timer += 1
        if self.wave_timer >= WAVE_DURATION:
            self.wave_timer = 0
            self.wave += 1
            self._spawn_floating_text(
                SCREEN_W / 2, SCREEN_H / 2,
                f"WAVE {self.wave}",
                pyxel.COLOR_YELLOW,
            )
            # Bonus HP on wave clear
            self.player.hp = min(PLAYER_MAX_HP, self.player.hp + 10)

    def _cleanup_dead_enemies(self) -> None:
        """Remove enemies with hp <= 0."""
        self.enemies = [e for e in self.enemies if e.hp > 0]

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        """Spawn burst of particles at position."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(10, 25),
                    color=color,
                    size=random.randint(1, 3),
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Spawn floating damage/heal text."""
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color, vy=-1.0)
        )

    # ── Overload animation ───────────────────────────────────────────────────

    def _update_overload_anim(self) -> None:
        """Update during the brief overload animation phase."""
        self._update_particles()
        self._update_floating_texts()
        self.overload_anim_timer -= 1
        if self.shake_timer > 0:
            self.shake_timer -= 1
        if self.overload_anim_timer <= 0:
            self.phase = Phase.PLAYING
            self._cleanup_dead_enemies()

    # ── Game over ────────────────────────────────────────────────────────────

    def _update_game_over(self) -> None:
        """Update during game over screen."""
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Main draw — dispatch by phase."""
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.PLAYING or self.phase == Phase.OVERLOAD_ANIM:
            self._draw_game_world()
            self._draw_ui()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_world()
            self._draw_ui()
            self._draw_game_over_overlay()

    def _draw_game_world(self) -> None:
        """Draw game entities: enemies, orbs, bullets, player, particles, texts."""
        # Screen shake offset
        shake_x = random.randint(-2, 2) if self.shake_timer > 0 else 0
        shake_y = random.randint(-2, 2) if self.shake_timer > 0 else 0

        ox = shake_x
        oy = shake_y

        # Orbs
        for orb in self.orbs:
            pyxel.circ(int(orb.x + ox), int(orb.y + oy), 3, pyxel.COLOR_CYAN)
            pyxel.circ(int(orb.x + ox), int(orb.y + oy), 1, pyxel.COLOR_WHITE)

        # Enemies
        for enemy in self.enemies:
            # Enemy body
            pyxel.circ(int(enemy.x + ox), int(enemy.y + oy), enemy.radius, pyxel.COLOR_RED)
            pyxel.circ(int(enemy.x + ox), int(enemy.y + oy), enemy.radius - 2, pyxel.COLOR_DARK_BLUE)
            # HP indicator (small bar above)
            hp_ratio = enemy.hp / (ENEMY_BASE_HP + self.wave * 5)
            bar_w = int(enemy.radius * 2 * hp_ratio)
            pyxel.rect(
                int(enemy.x + ox) - enemy.radius,
                int(enemy.y + oy) - enemy.radius - 5,
                bar_w,
                2,
                pyxel.COLOR_RED,
            )

        # Bullets
        for b in self.bullets:
            pyxel.circ(int(b.x + ox), int(b.y + oy), BULLET_RADIUS, pyxel.COLOR_YELLOW)

        # Player
        # Outer glow (charge indicator)
        charge_pulse = 0.5 + 0.5 * math.sin(pyxel.frame_count * 0.1)
        glow_radius = PLAYER_RADIUS + int(4 * (self.player.charge / CHARGE_MAX) * charge_pulse)
        if self.player.charge >= CHARGE_MAX:
            pyxel.circb(int(self.player.x + ox), int(self.player.y + oy), glow_radius, pyxel.COLOR_YELLOW)
        elif self.player.charge > 50:
            pyxel.circb(int(self.player.x + ox), int(self.player.y + oy), glow_radius, pyxel.COLOR_ORANGE)

        # Core body
        pyxel.circ(int(self.player.x + ox), int(self.player.y + oy), PLAYER_RADIUS, pyxel.COLOR_CYAN)
        pyxel.circ(int(self.player.x + ox), int(self.player.y + oy), PLAYER_RADIUS - 2, pyxel.COLOR_WHITE)
        pyxel.circ(int(self.player.x + ox), int(self.player.y + oy), 3, pyxel.COLOR_DARK_BLUE)

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x + ox), int(p.y + oy), p.color)

        # Floating texts
        for ft in self.floating_texts:
            alpha = min(1.0, ft.life / 20.0)
            if alpha > 0.3:
                pyxel.text(int(ft.x + ox), int(ft.y + oy), ft.text, ft.color)

    def _draw_ui(self) -> None:
        """Draw HUD: HP bar, charge bar, score, wave."""
        # HP bar (top-left)
        pyxel.rect(5, 5, 100, 6, pyxel.COLOR_DARK_BLUE)
        hp_ratio = max(0, self.player.hp / PLAYER_MAX_HP)
        hp_color = pyxel.COLOR_GREEN if hp_ratio > 0.5 else pyxel.COLOR_YELLOW if hp_ratio > 0.25 else pyxel.COLOR_RED
        pyxel.rect(5, 5, int(100 * hp_ratio), 6, hp_color)
        pyxel.text(5, 13, f"HP {self.player.hp}", pyxel.COLOR_WHITE)

        # Charge bar (top-right)
        bar_x = SCREEN_W - 105
        pyxel.rect(bar_x, 5, 100, 6, pyxel.COLOR_DARK_BLUE)
        charge_ratio = self.player.charge / CHARGE_MAX
        charge_color = pyxel.COLOR_YELLOW if charge_ratio >= 1.0 else pyxel.COLOR_CYAN
        pyxel.rect(bar_x, 5, int(100 * charge_ratio), 6, charge_color)
        label = "OVERLOAD READY" if charge_ratio >= 1.0 else f"CHG {int(self.player.charge)}"
        pyxel.text(bar_x, 13, label, pyxel.COLOR_WHITE)

        # Score (top-center)
        score_text = f"SCORE {self.score}"
        score_x = (SCREEN_W - len(score_text) * 4) // 2
        pyxel.text(score_x, 5, score_text, pyxel.COLOR_WHITE)

        # Wave indicator
        wave_text = f"WAVE {self.wave}"
        pyxel.text(5, SCREEN_H - 10, wave_text, pyxel.COLOR_YELLOW)

        # Wave progress bar (bottom)
        wave_progress = self.wave_timer / WAVE_DURATION
        prog_w = int(SCREEN_W * wave_progress)
        pyxel.rect(0, SCREEN_H - 3, prog_w, 3, pyxel.COLOR_DARK_BLUE)

        # Controls hint (bottom-right)
        if self.player.charge >= CHARGE_MAX:
            hint = "[SPACE] OVERLOAD"
            pyxel.text(SCREEN_W - len(hint) * 4 - 2, SCREEN_H - 10, hint, pyxel.COLOR_YELLOW)
        else:
            hint = "[WASD] Move"
            pyxel.text(SCREEN_W - len(hint) * 4 - 2, SCREEN_H - 10, hint, pyxel.COLOR_GRAY)

    def _draw_game_over_overlay(self) -> None:
        """Draw game over screen overlay."""
        # Dim background
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)

        # Title
        title = "GAME OVER"
        pyxel.text((SCREEN_W - len(title) * 4) // 2, 100, title, pyxel.COLOR_RED)

        # Score
        score_text = f"SCORE: {self.score}"
        pyxel.text((SCREEN_W - len(score_text) * 4) // 2, 120, score_text, pyxel.COLOR_WHITE)

        # Wave reached
        wave_text = f"WAVE: {self.wave}"
        pyxel.text((SCREEN_W - len(wave_text) * 4) // 2, 135, wave_text, pyxel.COLOR_YELLOW)

        # Restart hint
        hint = "PRESS [R] TO RETRY"
        pyxel.text((SCREEN_W - len(hint) * 4) // 2, 170, hint, pyxel.COLOR_WHITE)


# ── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for OVERLOAD prototype."""
    Game()


if __name__ == "__main__":
    main()
