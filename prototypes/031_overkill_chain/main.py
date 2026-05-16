"""OVERKILL CHAIN — Timing/overkill chain precision game.

Enemies march left toward your base. Click to attack — overkill damage
ripples through the enemy line, building combos. Closer enemies = higher
multiplier but more danger.

Core mechanic: overkill carryover chain (hook from idea #9, score 30.8).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config ──────────────────────────────────────────────────────────
W = 256
H = 192
BASE_X = 20  # Left edge of player's base

FPS = 60
ENEMY_H = 12
ENEMY_W = 14
ENEMY_Y_START = 80  # vertical center of enemy lane
ENEMY_Y_HALF = 16   # half-height of the lane (enemies vary within ±12)

# Enemy spawn config
SPAWN_INTERVAL = 45  # frames between spawns
INITIAL_SPEED = 0.35  # px per frame, increases over time

# Damage
CLICK_DAMAGE = 10
BASE_COMBO_MULT = 1.5  # each consecutive hit multiplies overkill by this

# Scoring
KILL_BASE_SCORE = 10
COMBO_SCORE_BONUS = 5

# Colors (from Pyxel's 16-color palette)
COL_BG = pyxel.COLOR_NAVY
COL_BASE = pyxel.COLOR_DARK_BLUE
COL_ENEMY = pyxel.COLOR_RED
COL_ENEMY_HIT = pyxel.COLOR_ORANGE
COL_PROJECTILE = pyxel.COLOR_YELLOW
COL_PARTICLE = pyxel.COLOR_WHITE
COL_TEXT = pyxel.COLOR_WHITE
COL_COMBO = pyxel.COLOR_LIGHT_BLUE
COL_DANGER = pyxel.COLOR_PINK
COL_UI_BG = pyxel.COLOR_BLACK

# ── Data classes ────────────────────────────────────────────────────


@dataclass(frozen=True)
class EnemyDef:
    """Enemy type definition."""

    name: str
    hp: int
    speed: float
    score: int
    color: int


# Enemy definitions for variety
ENEMY_DEFS: list[EnemyDef] = [
    EnemyDef("grunt", 8, 1.0, 5, pyxel.COLOR_RED),
    EnemyDef("runner", 5, 1.5, 8, pyxel.COLOR_ORANGE),
    EnemyDef("tank", 20, 0.6, 15, pyxel.COLOR_BROWN),
    EnemyDef("elite", 15, 1.0, 20, pyxel.COLOR_PINK),
]


@dataclass
class Enemy:
    """A single enemy instance."""

    defn: EnemyDef
    x: float
    y: float
    hp: int
    hit_timer: int = 0  # flash timer (frames)
    alive: bool = True

    @property
    def max_hp(self) -> int:
        return self.defn.hp

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.defn.hp if self.defn.hp > 0 else 0.0

    @property
    def danger_level(self) -> float:
        """0.0 = far right, 1.0 = at base."""
        return max(0.0, min(1.0, 1.0 - (self.x - BASE_X) / (W - BASE_X)))


@dataclass
class Particle:
    """Lightweight visual particle."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int
    size: int = 1


@dataclass
class FloatingText:
    """Score/damage text popup."""

    x: float
    y: float
    text: str
    life: int
    max_life: int
    color: int


# ── Phase enum ──────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game class ──────────────────────────────────────────────────────


class Game:
    """Main game class."""

    def __init__(self) -> None:
        pyxel.init(W, H, fps=FPS)
        self._mock_pyxel_input()  # safe defaults for headless import
        pyxel.run(self._update, self._draw)

    # ── Input mock for headless import ──────────────────────────────

    def _mock_pyxel_input(self) -> None:
        """Set safe defaults so btn/mouse don't crash on import."""
        try:
            pyxel.btn(0)
        except BaseException:
            # Pyxel not initialized yet — set up mock
            pass

    def reset(self) -> None:
        """Reset to a fresh game state."""
        self.phase = Phase.PLAYING
        self.enemies: list[Enemy] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hp = 100
        self.max_hp = 100
        self.wave = 1
        self.spawn_timer = 0
        self.frame = 0
        self.shake_timer = 0
        self.shake_intensity = 0
        self._chain_kills = 0  # kills in current overkill chain

    # ── Update ──────────────────────────────────────────────────────

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(
                pyxel.MOUSE_BUTTON_LEFT
            ):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floats()
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(
                pyxel.MOUSE_BUTTON_LEFT
            ):
                self.reset()
            return

        # PLAYING
        self.frame += 1
        self._update_spawns()
        self._update_enemies()
        self._update_input()
        self._update_particles()
        self._update_floats()
        self._update_shake()

        if self.hp <= 0:
            self.phase = Phase.GAME_OVER

    def _update_spawns(self) -> None:
        """Spawn new enemies at intervals."""
        self.spawn_timer += 1
        # Difficulty: spawn faster over time
        interval = max(15, SPAWN_INTERVAL - self.wave * 2)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            self._spawn_enemy()

    def _spawn_enemy(self) -> None:
        """Spawn a single enemy on the right edge."""
        # Pick enemy type based on wave
        max_idx = min(len(ENEMY_DEFS) - 1, self.wave // 3)
        defn = ENEMY_DEFS[random.randint(0, max_idx)]
        y = ENEMY_Y_START + random.randint(-ENEMY_Y_HALF, ENEMY_Y_HALF)
        speed_mult = 1.0 + (self.wave - 1) * 0.05
        enemy = Enemy(
            defn=defn,
            x=float(W),
            y=float(y),
            hp=defn.hp,
        )
        # Apply speed multiplier
        enemy.defn = EnemyDef(
            name=defn.name,
            hp=defn.hp,
            speed=defn.speed * speed_mult,
            score=defn.score,
            color=defn.color,
        )
        self.enemies.append(enemy)

    def _update_enemies(self) -> None:
        """Move enemies left; damage player if they reach base."""
        for e in self.enemies:
            if not e.alive:
                continue
            e.x -= e.defn.speed
            if e.hit_timer > 0:
                e.hit_timer -= 1
            # Reached base
            if e.x <= BASE_X:
                self.hp -= max(5, int(10 * e.danger_level))
                e.alive = False
                self.combo = 0
                self._chain_kills = 0
                self._spawn_particles(e.x, e.y, pyxel.COLOR_RED, 5)
                self.shake_timer = 8
                self.shake_intensity = 3

        self.enemies = [e for e in self.enemies if e.alive]

        # Wave escalation
        if self.frame % 600 == 0:
            self.wave += 1
            self._add_float(
                W / 2, H / 3, f"WAVE {self.wave}", pyxel.COLOR_LIGHT_BLUE
            )

    def _update_input(self) -> None:
        """Handle click to attack nearest enemy to cursor."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            self._try_attack(mx, my)

    def _try_attack(self, mx: float, my: float) -> None:
        """Attack the enemy closest to the click point."""
        # Find clicked enemy (within hitbox)
        target: Enemy | None = None
        best_dist = 999.0
        for e in self.enemies:
            if not e.alive:
                continue
            dx = e.x + ENEMY_W / 2 - mx
            dy = e.y - my
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < ENEMY_W and dist < best_dist:
                target = e
                best_dist = dist

        if target is None:
            # Miss — reset combo
            self.combo = 0
            self._chain_kills = 0
            return

        self._attack_enemy(target, CLICK_DAMAGE)

    def _attack_enemy(
        self, target: Enemy, damage: int, chain_depth: int = 0
    ) -> None:
        """Deal damage to an enemy, ripple overkill to next in line."""
        target.hp -= damage
        target.hit_timer = 6
        remaining = 0

        if target.hp <= 0:
            # Calculate overkill BEFORE zeroing HP
            remaining = abs(target.hp)
            target.alive = False
            target.hp = 0
            self._chain_kills += 1

            # Score: base + combo bonus + chain multiplier
            mult = 1 + self.combo * 0.5
            chain_mult = 1 + self._chain_kills * 0.3
            pts = int(target.defn.score * mult * chain_mult)
            self.score += pts

            # Danger zone bonus: closer enemies = more points
            danger_bonus = int(target.danger_level * pts * 0.5)
            self.score += danger_bonus

            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)

            self._add_float(
                target.x, target.y - 10, f"+{pts}", pyxel.COLOR_YELLOW
            )
            self._spawn_particles(target.x, target.y, target.defn.color, 8)

            if self._chain_kills >= 3:
                self.shake_timer = 6
                self.shake_intensity = 2
        else:
            # Hit but not killed
            pts = max(1, self.combo // 2)
            self.score += pts
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self._add_float(target.x, target.y - 10, f"{damage}", pyxel.COLOR_WHITE)

        # Ripple overkill to nearest enemy further left
        if remaining > 0:
            next_enemy = self._find_next_enemy_in_line(target)
            if next_enemy is not None:
                chain_damage = int(remaining * (1.0 + chain_depth * 0.2))
                chain_damage = max(1, chain_damage)
                self._attack_enemy(next_enemy, chain_damage, chain_depth + 1)

    def _find_next_enemy_in_line(self, source: Enemy) -> Enemy | None:
        """Find the alive enemy closest to the left of the source."""
        best: Enemy | None = None
        best_dist = 999.0
        for e in self.enemies:
            if not e.alive or e is source:
                continue
            if e.x < source.x:
                dist = source.x - e.x
                if dist < best_dist:
                    best = e
                    best_dist = dist
        return best

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15  # gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y -= 0.5
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _update_shake(self) -> None:
        if self.shake_timer > 0:
            self.shake_timer -= 1
        else:
            self.shake_intensity = 0

    # ── Drawing ─────────────────────────────────────────────────────

    def _draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
            return
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_game()

    def _draw_game(self) -> None:
        pyxel.cls(COL_BG)

        # Screen shake
        ox = 0
        oy = 0
        if self.shake_timer > 0:
            ox = random.randint(-self.shake_intensity, self.shake_intensity)
            oy = random.randint(-self.shake_intensity, self.shake_intensity)

        pyxel.camera(ox, oy)

        # Draw base
        pyxel.rect(0, 0, BASE_X, H, COL_BASE)
        pyxel.rectb(0, 0, BASE_X, H, pyxel.COLOR_LIGHT_BLUE)
        # Base HP bar
        hp_ratio = self.hp / self.max_hp
        pyxel.rect(2, 4, int((BASE_X - 4) * hp_ratio), 4, pyxel.COLOR_LIME)
        pyxel.rectb(2, 4, BASE_X - 4, 4, pyxel.COLOR_WHITE)

        # Draw danger zone indicator
        danger_x = BASE_X + 40
        pyxel.line(danger_x, ENEMY_Y_START - 20, danger_x, ENEMY_Y_START + 20, pyxel.COLOR_RED)

        # Draw enemies
        for e in self.enemies:
            if not e.alive:
                continue
            col = e.defn.color
            if e.hit_timer > 0:
                col = COL_ENEMY_HIT
            pyxel.rect(int(e.x), int(e.y) - ENEMY_H // 2, ENEMY_W, ENEMY_H, col)
            # HP bar
            bar_w = ENEMY_W
            bar_hp = int(bar_w * e.hp_ratio)
            pyxel.rect(int(e.x), int(e.y) - ENEMY_H // 2 - 3, bar_hp, 2, pyxel.COLOR_LIME)

        # Draw particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Draw floating texts
        for f in self.floats:
            pyxel.text(int(f.x), int(f.y), f.text, f.color)

        pyxel.camera(0, 0)

        # ── HUD (screen-space, no shake) ──
        # Score
        pyxel.text(4, H - 12, f"SCORE {self.score}", COL_TEXT)
        # Combo
        if self.combo > 0:
            combo_col = COL_COMBO if self.combo < 5 else pyxel.COLOR_YELLOW
            pyxel.text(W - 60, H - 12, f"COMBO x{self.combo}", combo_col)
        # Wave
        pyxel.text(W // 2 - 20, H - 12, f"WV{self.wave}", COL_TEXT)
        # HP
        hp_col = pyxel.COLOR_LIME if self.hp > 50 else pyxel.COLOR_ORANGE if self.hp > 20 else pyxel.COLOR_RED
        pyxel.text(4, 2, f"HP {self.hp}", hp_col)

    def _draw_title(self) -> None:
        pyxel.cls(COL_BG)
        pyxel.text(W // 2 - 50, H // 2 - 30, "OVERKILL CHAIN", pyxel.COLOR_YELLOW)
        pyxel.text(W // 2 - 55, H // 2 - 10, "Click enemies to attack", COL_TEXT)
        pyxel.text(W // 2 - 60, H // 2 + 5, "Overkill ripples to the left", COL_TEXT)
        pyxel.text(W // 2 - 50, H // 2 + 25, "SPACE/CLICK to start", COL_TEXT)
        pyxel.text(W // 2 - 65, H // 2 + 45, "Closer enemies = more points", COL_TEXT)

    def _draw_game_over(self) -> None:
        pyxel.cls(COL_BG)
        pyxel.text(W // 2 - 40, H // 2 - 30, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(W // 2 - 30, H // 2 - 10, f"SCORE {self.score}", COL_TEXT)
        pyxel.text(W // 2 - 30, H // 2 + 5, f"MAX COMBO {self.max_combo}", COL_TEXT)
        pyxel.text(W // 2 - 50, H // 2 + 25, "SPACE/CLICK to retry", COL_TEXT)

        # Particles still render
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    # ── Helpers ─────────────────────────────────────────────────────

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = random.random() * 6.28
            speed = random.random() * 2.0 + 0.5
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(10, 25),
                    max_life=25,
                    color=color,
                )
            )

    def _add_float(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floats.append(
            FloatingText(
                x=x,
                y=y,
                text=text,
                life=40,
                max_life=40,
                color=color,
            )
        )


# ── Entry point ─────────────────────────────────────────────────────


def main() -> None:
    g = Game()
    g.reset()


if __name__ == "__main__":
    main()
