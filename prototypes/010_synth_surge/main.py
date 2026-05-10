"""Synth Surge — Auto-shooter with color-match synthesis.

Collect 3 same-color shards to trigger devastating super abilities.
Risk/reward: grab shards you need, dodge shards that break your chain.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ───────────────────────────────────────────────────────
SCREEN_W = 400
SCREEN_H = 300
PLAYER_RADIUS = 6
PLAYER_SPEED = 1.8
PLAYER_MAX_HP = 5
FIRE_COOLDOWN = 12  # frames between auto-shots
BULLET_SPEED = 4.5
BULLET_DAMAGE = 1
ENEMY_BASE_HP = 1
ENEMY_SPEED = 1.2
ENEMY_RADIUS = 5
ENEMY_DAMAGE = 1
ENEMY_SPAWN_BASE = 50  # frames between spawns (initial)
SHARD_RADIUS = 4
SHARD_LIFETIME = 360  # frames (6 seconds)
SYNTH_ANIM_DUR = 20  # frames for synthesis flash
FREEZE_DURATION = 180  # frames (3 seconds)
OVERRIDE_DURATION = 240  # frames (4 seconds)
PARTICLE_COUNT = 20
MAX_ENEMIES = 20
INVINCIBILITY_FRAMES = 30  # after taking damage

# ── Enums ───────────────────────────────────────────────────────────
class Chroma(Enum):
    RED = auto()
    BLUE = auto()
    GREEN = auto()
    YELLOW = auto()


class Phase(Enum):
    PLAYING = auto()
    SYNTH_ANIM = auto()
    GAME_OVER = auto()


# ── Color mapping ───────────────────────────────────────────────────
CHROMA_COL: dict[Chroma, int] = {
    Chroma.RED: 8,
    Chroma.BLUE: 6,
    Chroma.GREEN: 3,
    Chroma.YELLOW: 10,
}

CHROMA_NAME: dict[Chroma, str] = {
    Chroma.RED: "INCINERATE",
    Chroma.BLUE: "FROST WALL",
    Chroma.GREEN: "REGEN",
    Chroma.YELLOW: "OVERRIDE",
}

CHROMA_LABEL: dict[Chroma, str] = {
    Chroma.RED: "R",
    Chroma.BLUE: "B",
    Chroma.GREEN: "G",
    Chroma.YELLOW: "Y",
}


# ── Data classes ────────────────────────────────────────────────────
@dataclass
class Player:
    x: float
    y: float
    hp: int = PLAYER_MAX_HP
    fire_timer: int = 0
    invuln: int = 0
    override_timer: int = 0


@dataclass
class Enemy:
    x: float
    y: float
    hp: int
    speed: float
    radius: float
    chroma: Chroma
    frozen: int = 0


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    damage: int = BULLET_DAMAGE


@dataclass
class Shard:
    x: float
    y: float
    chroma: Chroma
    life: int = SHARD_LIFETIME


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    col: int
    life: int
    max_life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    col: int
    life: int
    vy: float = -1.0


# ── Game class ──────────────────────────────────────────────────────
class SynthSurge:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Synth Surge", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.PLAYING
        self.player: Player = Player(x=SCREEN_W / 2, y=SCREEN_H - 40)
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.shards: list[Shard] = []
        self.particles: list[Particle] = []
        self.floaters: list[FloatingText] = []
        self.synth_slots: list[Chroma | None] = [None, None, None]
        self.synth_anim_timer: int = 0
        self.synth_color: int = 0
        self.spawn_timer: int = 0
        self.score: int = 0
        self.synthesis_count: int = 0
        self.game_time: int = 0
        self.freeze_timer: int = 0
        self.shake_timer: int = 0
        self.shake_intensity: int = 0

    # ── Update ────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.PLAYING:
            self._update_player()
            self._update_bullets()
            self._update_enemies()
            self._update_shards()
            self._spawn_enemies()
            self._update_particles()
            self._update_floaters()
            self._check_synthesis()
            self._update_timers()
            self.game_time += 1
        elif self.phase == Phase.SYNTH_ANIM:
            self.synth_anim_timer -= 1
            self._update_particles()
            self._update_floaters()
            if self.synth_anim_timer <= 0:
                self.phase = Phase.PLAYING
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()

    def _update_timers(self) -> None:
        if self.freeze_timer > 0:
            self.freeze_timer -= 1
        if self.shake_timer > 0:
            self.shake_timer -= 1
        if self.player.invuln > 0:
            self.player.invuln -= 1
        if self.player.override_timer > 0:
            self.player.override_timer -= 1

    def _update_player(self) -> None:
        p = self.player
        dx = dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_SPEED

        # Diagonal normalization
        if dx != 0 and dy != 0:
            inv_sqrt2 = 1.0 / math.sqrt(2.0)
            dx *= inv_sqrt2
            dy *= inv_sqrt2

        p.x = max(PLAYER_RADIUS, min(SCREEN_W - PLAYER_RADIUS, p.x + dx))
        p.y = max(PLAYER_RADIUS, min(SCREEN_H - PLAYER_RADIUS, p.y + dy))

        # Auto-fire at nearest enemy
        p.fire_timer -= 1
        if p.fire_timer <= 0:
            target = self._find_nearest_enemy(p.x, p.y)
            if target is not None:
                self._fire_bullet(p.x, p.y, target)
                cooldown = FIRE_COOLDOWN // 2 if p.override_timer > 0 else FIRE_COOLDOWN
                p.fire_timer = cooldown

    def _find_nearest_enemy(self, x: float, y: float) -> Enemy | None:
        best: Enemy | None = None
        best_dist = float("inf")
        for e in self.enemies:
            dist = (e.x - x) ** 2 + (e.y - y) ** 2
            if dist < best_dist:
                best_dist = dist
                best = e
        return best

    def _fire_bullet(self, x: float, y: float, target: Enemy) -> None:
        dx = target.x - x
        dy = target.y - y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1:
            return
        vx = (dx / dist) * BULLET_SPEED
        vy = (dy / dist) * BULLET_SPEED
        self.bullets.append(Bullet(x=x, y=y, vx=vx, vy=vy))

    def _update_bullets(self) -> None:
        new_bullets: list[Bullet] = []
        for b in self.bullets:
            b.x += b.vx
            b.y += b.vy
            # Remove if off-screen
            if b.x < 0 or b.x > SCREEN_W or b.y < 0 or b.y > SCREEN_H:
                continue
            # Check collision with enemies
            hit = False
            for e in self.enemies:
                dist2 = (b.x - e.x) ** 2 + (b.y - e.y) ** 2
                if dist2 < (e.radius + 3) ** 2:
                    e.hp -= b.damage
                    hit = True
                    self._spawn_particles(b.x, b.y, CHROMA_COL[e.chroma], 3)
                    break
            if not hit:
                new_bullets.append(b)
        self.bullets = new_bullets

    def _update_enemies(self) -> None:
        new_enemies: list[Enemy] = []
        for e in self.enemies:
            if e.hp <= 0:
                self._on_enemy_killed(e)
                continue
            if e.frozen > 0:
                e.frozen -= 1
                new_enemies.append(e)
                continue
            if self.freeze_timer > 0:
                new_enemies.append(e)
                continue
            # Move toward player
            dx = self.player.x - e.x
            dy = self.player.y - e.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 1:
                e.x += (dx / dist) * e.speed
                e.y += (dy / dist) * e.speed
            # Damage player on contact
            pdist2 = (e.x - self.player.x) ** 2 + (e.y - self.player.y) ** 2
            contact_dist = e.radius + PLAYER_RADIUS
            if pdist2 < contact_dist * contact_dist and self.player.invuln <= 0:
                self.player.hp -= ENEMY_DAMAGE
                self.player.invuln = INVINCIBILITY_FRAMES
                self._spawn_particles(self.player.x, self.player.y, 8, 6)
                self._add_floater(self.player.x, self.player.y - 10, "-1", 8)
                self.shake_timer = 8
                self.shake_intensity = 3
                if self.player.hp <= 0:
                    self.phase = Phase.GAME_OVER
                    self._spawn_particles(self.player.x, self.player.y, 8, 30)
                    return
            new_enemies.append(e)
        self.enemies = new_enemies

    def _on_enemy_killed(self, e: Enemy) -> None:
        self._spawn_particles(e.x, e.y, CHROMA_COL[e.chroma], 8)
        self.score += 10
        # Drop a shard
        self.shards.append(Shard(x=e.x, y=e.y, chroma=e.chroma))

    def _update_shards(self) -> None:
        p = self.player
        new_shards: list[Shard] = []
        for s in self.shards:
            s.life -= 1
            if s.life <= 0:
                continue
            # Auto-collect within pickup range (20px)
            dist2 = (s.x - p.x) ** 2 + (s.y - p.y) ** 2
            if dist2 < 20 * 20:
                self._add_shard_to_slots(s.chroma)
                self._spawn_particles(s.x, s.y, CHROMA_COL[s.chroma], 4)
                continue
            new_shards.append(s)
        self.shards = new_shards

    def _add_shard_to_slots(self, chroma: Chroma) -> None:
        """Add a shard to the synthesis slots (FIFO queue)."""
        slots = self.synth_slots
        # Shift left and add new
        slots[0] = slots[1]
        slots[1] = slots[2]
        slots[2] = chroma

    def _check_synthesis(self) -> None:
        """If all 3 slots match, trigger synthesis."""
        slots = self.synth_slots
        if slots[0] is not None and slots[0] == slots[1] == slots[2]:
            self._trigger_synthesis(slots[0])
            self.synth_slots = [None, None, None]

    def _trigger_synthesis(self, chroma: Chroma) -> None:
        self.synthesis_count += 1
        self.synth_color = CHROMA_COL[chroma]
        self.synth_anim_timer = SYNTH_ANIM_DUR
        self.phase = Phase.SYNTH_ANIM
        self.shake_timer = SYNTH_ANIM_DUR
        self.shake_intensity = 5

        # Screen-center particles
        for _ in range(PARTICLE_COUNT * 2):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            self.particles.append(Particle(
                x=SCREEN_W / 2, y=SCREEN_H / 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                col=self.synth_color,
                life=SYNTH_ANIM_DUR,
                max_life=SYNTH_ANIM_DUR,
            ))

        name = CHROMA_NAME[chroma]
        self._add_floater(SCREEN_W / 2, SCREEN_H / 2 - 10, f"SYNTH: {name}", self.synth_color)

        # Apply super effect
        if chroma == Chroma.RED:
            self._super_incinerate()
        elif chroma == Chroma.BLUE:
            self._super_freeze()
        elif chroma == Chroma.GREEN:
            self._super_regen()
        elif chroma == Chroma.YELLOW:
            self._super_override()

    def _super_incinerate(self) -> None:
        """Destroy all enemies on screen."""
        score_bonus = len(self.enemies) * 50
        self.score += score_bonus
        for e in self.enemies:
            self._spawn_particles(e.x, e.y, 8, 10)
        self.enemies.clear()

    def _super_freeze(self) -> None:
        """Freeze all enemies for 3 seconds."""
        self.freeze_timer = FREEZE_DURATION

    def _super_regen(self) -> None:
        """Restore 2 HP (up to max)."""
        healed = min(2, PLAYER_MAX_HP - self.player.hp)
        self.player.hp += healed
        self._add_floater(self.player.x, self.player.y - 14, f"+{healed}HP", 3)

    def _super_override(self) -> None:
        """Double fire rate for 4 seconds."""
        self.player.override_timer = OVERRIDE_DURATION

    def _spawn_enemies(self) -> None:
        if len(self.enemies) >= MAX_ENEMIES:
            return
        # Spawn rate accelerates over time
        spawn_rate = max(10, ENEMY_SPAWN_BASE - self.game_time // 600)
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = spawn_rate
            self._spawn_one_enemy()

    def _spawn_one_enemy(self) -> None:
        # Pick edge spawn point
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

        # Difficulty scaling over time
        wave = self.game_time // 600  # every 10 seconds
        chroma = random.choice(list(Chroma))
        hp = ENEMY_BASE_HP + wave // 2
        speed = ENEMY_SPEED + wave * 0.15

        self.enemies.append(Enemy(
            x=x, y=y, hp=hp, speed=speed,
            radius=ENEMY_RADIUS, chroma=chroma,
        ))

    def _update_particles(self) -> None:
        new_p: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                new_p.append(p)
        self.particles = new_p

    def _update_floaters(self) -> None:
        new_f: list[FloatingText] = []
        for f in self.floaters:
            f.y += f.vy
            f.life -= 1
            if f.life > 0:
                new_f.append(f)
        self.floaters = new_f

    def _spawn_particles(self, x: float, y: float, col: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 3)
            life = random.randint(8, 20)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                col=col, life=life, max_life=life,
            ))

    def _add_floater(self, x: float, y: float, text: str, col: int) -> None:
        self.floaters.append(FloatingText(x=x, y=y, text=text, col=col, life=30))

    # ── Draw ──────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(0)

        shake_x = 0
        shake_y = 0
        if self.shake_timer > 0:
            shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = random.randint(-self.shake_intensity, self.shake_intensity)
            pyxel.camera(shake_x, shake_y)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_enemies()
        self._draw_shards()
        self._draw_player()
        self._draw_bullets()
        self._draw_particles()
        self._draw_floaters()
        self._draw_ui()

        if self.phase == Phase.SYNTH_ANIM:
            self._draw_synthesis_flash()

        pyxel.camera(0, 0)

    def _draw_player(self) -> None:
        p = self.player
        # Blink during invulnerability
        if p.invuln > 0 and p.invuln % 4 < 2:
            return
        col = 7
        if p.override_timer > 0:
            col = 10  # yellow glow
        pyxel.circ(p.x, p.y, PLAYER_RADIUS, col)
        pyxel.circ(p.x, p.y, PLAYER_RADIUS - 2, 0)
        # Inner dot
        pyxel.pset(p.x, p.y, col)

    def _draw_enemies(self) -> None:
        for e in self.enemies:
            col = CHROMA_COL[e.chroma]
            if e.frozen > 0 or self.freeze_timer > 0:
                col = 12  # light blue when frozen
            if e.hp > 1:
                # Larger/tougher enemies have a ring
                pyxel.circb(e.x, e.y, e.radius + 1, col)
            pyxel.circ(e.x, e.y, e.radius, col)
            # Draw HP for multi-hit enemies
            if e.hp > 1:
                pyxel.text(e.x - 2, e.y - 2, str(e.hp), 0)

    def _draw_shards(self) -> None:
        for s in self.shards:
            col = CHROMA_COL[s.chroma]
            # Blink when about to expire
            if s.life < 60 and s.life % 8 < 4:
                col = (col + 7) % 16 or 7
            pyxel.rect(s.x - SHARD_RADIUS, s.y - SHARD_RADIUS,
                       SHARD_RADIUS * 2, SHARD_RADIUS * 2, col)
            # Label
            label = CHROMA_LABEL[s.chroma]
            pyxel.text(s.x - 1, s.y - 2, label, 0)

    def _draw_bullets(self) -> None:
        for b in self.bullets:
            pyxel.pset(b.x, b.y, 7)
            pyxel.pset(b.x - 1, b.y, 7)
            pyxel.pset(b.x + 1, b.y, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            col = p.col if alpha > 0.5 else 0
            pyxel.pset(p.x, p.y, col)

    def _draw_floaters(self) -> None:
        for f in self.floaters:
            alpha = f.life / 30.0
            col = f.col if alpha > 0.3 else 0
            pyxel.text(f.x - len(f.text) * 2, f.y, f.text, col)

    def _draw_ui(self) -> None:
        # Synthesis slots (top center)
        slot_x = SCREEN_W // 2 - 30
        slot_y = 6
        for i in range(3):
            px = slot_x + i * 22
            chroma = self.synth_slots[i]
            col = CHROMA_COL[chroma] if chroma is not None else 13
            pyxel.rectb(px, slot_y, 16, 16, col)
            if chroma is not None:
                label = CHROMA_LABEL[chroma]
                pyxel.text(px + 5, slot_y + 4, label, col)
            else:
                # Empty slot dot
                pyxel.pset(px + 8, slot_y + 8, 13)

        # Score and time (top left)
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", 7)
        pyxel.text(4, 12, f"SYNTH:{self.synthesis_count}", 10)
        time_sec = self.game_time // 60
        pyxel.text(SCREEN_W - 40, 4, f"T:{time_sec:03d}", 7)

        # HP bar (bottom center)
        bar_w = 80
        bar_x = SCREEN_W // 2 - bar_w // 2
        bar_y = SCREEN_H - 12
        pyxel.rectb(bar_x, bar_y, bar_w, 6, 7)
        hp_ratio = self.player.hp / PLAYER_MAX_HP
        hp_col = 3 if hp_ratio > 0.5 else 8
        pyxel.rect(bar_x + 1, bar_y + 1, int((bar_w - 1) * hp_ratio), 4, hp_col)

        # Active effects indicators
        fx_y = SCREEN_H - 24
        if self.freeze_timer > 0:
            sec = self.freeze_timer // 60 + 1
            pyxel.text(4, fx_y, f"FREEZE:{sec}s", 12)
        if self.player.override_timer > 0:
            sec = self.player.override_timer // 60 + 1
            pyxel.text(SCREEN_W - 60, fx_y, f"OVRD:{sec}s", 10)

    def _draw_synthesis_flash(self) -> None:
        """Flash the screen during synthesis animation."""
        alpha = self.synth_anim_timer / SYNTH_ANIM_DUR
        # Flash full screen with synth color
        if alpha > 0.5:
            flash_col = self.synth_color
        elif int(self.synth_anim_timer) % 4 < 2:
            flash_col = self.synth_color
        else:
            flash_col = 0
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, flash_col)

    def _draw_game_over(self) -> None:
        # Dim background
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 0)
        # Draw remaining particles (explosion aftermath)
        self._draw_particles()

        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 20, "GAME OVER", 8)
        pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2, f"SCORE: {self.score:06d}", 7)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 10, f"SYNTHESIS: {self.synthesis_count}", 10)
        time_sec = self.game_time // 60
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 + 20, f"TIME: {time_sec}s", 7)
        pyxel.text(SCREEN_W // 2 - 45, SCREEN_H // 2 + 35, "PRESS [R] TO RETRY", 13)


# ── Entry point ────────────────────────────────────────────────────
def main() -> None:
    SynthSurge()


if __name__ == "__main__":
    main()
