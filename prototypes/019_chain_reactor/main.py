"""CHAIN REACTOR — Top-down arena shooter with color-chain propagation.

Reinterpreted from idea #1 (score 31.95): propagation/chain reaction hooks
applied to a top-down shmup. Destroy one enemy to trigger cascading
same-color chain reactions for massive score multipliers.

The fun moment: watching a single well-placed shot trigger a cascading
chain reaction through a dense cluster of same-colored enemies.
"""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pyxel

# ═══════════════════════════════════════════════════════════════
#  Config
# ═══════════════════════════════════════════════════════════════

WIDTH = 400
HEIGHT = 300
PLAYER_SPEED = 2.0
BULLET_SPEED = 5.0
CHAIN_RADIUS = 55.0
MAX_HEAT = 100.0
HEAT_PER_SHOT = 2.5
HEAT_DECAY = 0.4
HEAT_OVERHEAT_DECAY = 1.5
OVERHEAT_FRAMES = 50
INVULN_FRAMES = 90
ENEMY_RADIUS = 7
PLAYER_RADIUS = 6
BULLET_RADIUS = 3
COMBO_DISPLAY_FRAMES = 45
MAX_ENEMIES = 40

# Color palette: 4 element colors
COLOR_PYXEL: list[int] = [
    pyxel.COLOR_RED,     # 0: Fire
    pyxel.COLOR_CYAN,    # 1: Ice
    pyxel.COLOR_YELLOW,  # 2: Lightning
    pyxel.COLOR_LIME,    # 3: Nature
]
COLOR_DARK: list[int] = [
    pyxel.COLOR_BROWN,
    pyxel.COLOR_DARK_BLUE,
    pyxel.COLOR_ORANGE,
    pyxel.COLOR_GREEN,
]
COLOR_NAME: list[str] = ["FIRE", "ICE", "LIGHTNING", "NATURE"]


# ═══════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class Enemy:
    """An enemy on the field, moving toward the player."""

    x: float
    y: float
    color: int  # 0-3 index into COLOR_PYXEL
    speed: float = 0.8


@dataclass
class Bullet:
    """A player bullet in flight."""

    x: float
    y: float
    vx: float
    vy: float


@dataclass
class Particle:
    """Visual particle for explosions and effects."""

    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    radius: int = 2


@dataclass
class FloatingText:
    """Score popup / combo indicator text that floats up and fades."""

    x: float
    y: float
    text: str
    color: int
    life: int


# ═══════════════════════════════════════════════════════════════
#  Phase
# ═══════════════════════════════════════════════════════════════


class Phase(enum.Enum):
    TITLE = enum.auto()
    PLAYING = enum.auto()
    OVERHEAT = enum.auto()
    GAME_OVER = enum.auto()


# ═══════════════════════════════════════════════════════════════
#  Game
# ═══════════════════════════════════════════════════════════════


class ChainReactor:
    """Top-down arena shooter: trigger color-chain reactions for score."""

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="CHAIN REACTOR", display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State ──

    def reset(self) -> None:
        """Reset all game state for a new session."""
        self.phase: Phase = Phase.TITLE
        self.player_x: float = WIDTH / 2
        self.player_y: float = HEIGHT - 50
        self.hp: int = 3
        self.heat: float = 0.0
        self.score: int = 0
        self.wave: int = 1
        self.kill_count: int = 0
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.combo: int = 0
        self.combo_timer: int = 0
        self.max_combo: int = 0
        self.overheat_timer: int = 0
        self.invuln: int = 0
        self.shake: int = 0
        self.best_score: int = 0
        self.frame: int = 0
        self._spawn_timer: int = 30  # frames until next spawn wave

    # ── Update ──

    def update(self) -> None:
        """Main update loop, dispatched by phase."""
        self.frame += 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.OVERHEAT:
            self._update_overheat()
        elif self.phase == Phase.GAME_OVER:
            self._update_gameover()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        """Initialize a new game run."""
        self.phase = Phase.PLAYING
        self.player_x = WIDTH / 2
        self.player_y = HEIGHT - 50
        self.hp = 3
        self.heat = 0.0
        self.score = 0
        self.wave = 1
        self.kill_count = 0
        self.enemies.clear()
        self.bullets.clear()
        self.particles.clear()
        self.texts.clear()
        self.combo = 0
        self.combo_timer = 0
        self.max_combo = 0
        self.overheat_timer = 0
        self.invuln = 0
        self.shake = 0
        self._spawn_timer = 30

    def _update_playing(self) -> None:
        """Core gameplay update."""
        # Timers
        if self.invuln > 0:
            self.invuln -= 1
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        # Heat decay
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

        # Movement (WASD / arrow keys)
        self._update_movement()

        # Shooting (mouse button held + not overheated)
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.heat < MAX_HEAT:
            self._shoot_bullet()

        # Update projectiles
        self._update_bullets()

        # Update enemy movement
        self._update_enemies()

        # Spawn wave
        self._spawn_enemies()

        # Collisions
        self._check_bullet_collisions()
        self._check_player_hit()

        # Effects
        self._update_particles()
        self._update_texts()

        # Shake decay
        if self.shake > 0:
            self.shake -= 1

    def _update_movement(self) -> None:
        """Handle player movement input."""
        dy = 0.0
        dx = 0.0
        if pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP):
            dy -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN):
            dy += PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT):
            dx -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT):
            dx += PLAYER_SPEED

        # Diagonal normalization
        if dx != 0 and dy != 0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv

        self.player_x = max(PLAYER_RADIUS, min(WIDTH - PLAYER_RADIUS, self.player_x + dx))
        self.player_y = max(PLAYER_RADIUS, min(HEIGHT - PLAYER_RADIUS, self.player_y + dy))

    def _shoot_bullet(self) -> None:
        """Fire a bullet toward the mouse cursor."""
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        dx = mx - self.player_x
        dy = my - self.player_y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dx, dy = 0.0, -1.0
            dist = 1.0
        vx = (dx / dist) * BULLET_SPEED
        vy = (dy / dist) * BULLET_SPEED
        self.bullets.append(Bullet(self.player_x, self.player_y, vx, vy))
        self.heat += HEAT_PER_SHOT
        if self.heat >= MAX_HEAT:
            self.heat = MAX_HEAT
            self.phase = Phase.OVERHEAT
            self.overheat_timer = OVERHEAT_FRAMES
            self.shake = 12
            # Spawn overheat particles around player
            for _ in range(15):
                angle = random.uniform(0, math.pi * 2)
                spd = random.uniform(0.5, 2.0)
                self.particles.append(
                    Particle(
                        self.player_x, self.player_y,
                        math.cos(angle) * spd, math.sin(angle) * spd,
                        3,  # white-ish particle color index
                        random.randint(10, 20),
                        radius=4,
                    )
                )

    def _update_bullets(self) -> None:
        """Move bullets; remove off-screen ones."""
        alive: list[Bullet] = []
        for b in self.bullets:
            b.x += b.vx
            b.y += b.vy
            if -BULLET_RADIUS <= b.x <= WIDTH + BULLET_RADIUS and -BULLET_RADIUS <= b.y <= HEIGHT + BULLET_RADIUS:
                alive.append(b)
        self.bullets = alive

    def _update_enemies(self) -> None:
        """Move each enemy toward the player."""
        for e in self.enemies:
            dx = self.player_x - e.x
            dy = self.player_y - e.y
            dist = math.hypot(dx, dy)
            if dist > 0.5:
                e.x += (dx / dist) * e.speed
                e.y += (dy / dist) * e.speed

    def _spawn_enemies(self) -> None:
        """Spawn a wave of enemies from screen edges."""
        if self._spawn_timer > 0:
            self._spawn_timer -= 1
            return

        # Scale spawn count and speed with wave
        count = min(3 + self.wave * 2, MAX_ENEMIES - len(self.enemies))
        count = max(1, count)
        self._spawn_timer = max(15, 50 - self.wave * 3)

        for _ in range(count):
            side = random.randint(0, 3)
            margin = ENEMY_RADIUS + 4
            if side == 0:  # top
                x = random.uniform(margin, WIDTH - margin)
                y = float(-margin)
            elif side == 1:  # right
                x = WIDTH + margin
                y = random.uniform(margin, HEIGHT - margin)
            elif side == 2:  # bottom
                x = random.uniform(margin, WIDTH - margin)
                y = HEIGHT + margin
            else:  # left
                x = float(-margin)
                y = random.uniform(margin, HEIGHT - margin)

            color = random.randint(0, 3)
            speed = 0.5 + self.wave * 0.06 + random.uniform(-0.1, 0.15)
            speed = max(0.3, min(speed, 2.5))
            self.enemies.append(Enemy(x, y, color, speed=speed))

    def _check_bullet_collisions(self) -> None:
        """Detect bullet-enemy hits and trigger chain reactions."""
        enemies_killed: set[int] = set()
        bullets_used: set[int] = set()

        for bi, b in enumerate(self.bullets):
            for ei, e in enumerate(self.enemies):
                if ei in enemies_killed:
                    continue
                if math.hypot(b.x - e.x, b.y - e.y) < BULLET_RADIUS + ENEMY_RADIUS:
                    bullets_used.add(bi)
                    self._chain_propagate(ei, e.color, enemies_killed)
                    break

        # Remove used bullets
        self.bullets = [b for i, b in enumerate(self.bullets) if i not in bullets_used]

        if not enemies_killed:
            return

        chain_len = len(enemies_killed)
        self.kill_count += chain_len

        # Score calculation
        base_score = 10
        points = base_score * chain_len
        if chain_len >= 2:
            points = base_score * chain_len * chain_len
            self.combo = chain_len
            self.combo_timer = COMBO_DISPLAY_FRAMES
            self.max_combo = max(self.max_combo, self.combo)
            self.shake = max(self.shake, min(10, chain_len // 2))

        self.score += points

        # Effects: particles + floating text at chain center
        cx: float = 0.0
        cy: float = 0.0
        valid = 0
        for ei in enemies_killed:
            if ei < len(self.enemies):
                e = self.enemies[ei]
                cx += e.x
                cy += e.y
                valid += 1
        if valid > 0:
            cx /= valid
            cy /= valid

        if chain_len >= 2:
            self.texts.append(FloatingText(cx, cy, f"CHAIN x{chain_len}!", pyxel.COLOR_YELLOW, 40))
            self.texts.append(FloatingText(cx, cy + 10, f"+{points}", pyxel.COLOR_WHITE, 35))
        elif valid > 0:
            self.texts.append(FloatingText(cx, cy, f"+{points}", pyxel.COLOR_WHITE, 25))

        # Spawn particles for each killed enemy
        for ei in sorted(enemies_killed, reverse=True):
            if ei < len(self.enemies):
                e = self.enemies[ei]
                self._spawn_explosion(e.x, e.y, e.color, chain_len)
                del self.enemies[ei]

    def _chain_propagate(self, start_idx: int, color: int, collected: set[int]) -> None:
        """BFS: propagate chain to all same-color enemies within CHAIN_RADIUS."""
        collected.add(start_idx)
        queue: list[int] = [start_idx]

        while queue:
            cur_idx = queue.pop(0)
            cur = self.enemies[cur_idx]
            for ei, e in enumerate(self.enemies):
                if ei in collected:
                    continue
                if e.color != color:
                    continue
                if math.hypot(cur.x - e.x, cur.y - e.y) <= CHAIN_RADIUS:
                    collected.add(ei)
                    queue.append(ei)

    def _spawn_explosion(self, x: float, y: float, color_idx: int, chain_size: int) -> None:
        """Spawn explosion particles at a position."""
        count = 5 + chain_size * 3
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(0.5, 2.5)
            life = random.randint(8, 22)
            self.particles.append(
                Particle(
                    x, y,
                    math.cos(angle) * spd,
                    math.sin(angle) * spd,
                    color_idx,
                    life,
                    radius=random.randint(1, 4),
                )
            )

    def _check_player_hit(self) -> None:
        """Check enemy-player collisions."""
        if self.invuln > 0:
            return
        for ei, e in enumerate(self.enemies):
            if math.hypot(self.player_x - e.x, self.player_y - e.y) < PLAYER_RADIUS + ENEMY_RADIUS:
                self.hp -= 1
                self.invuln = INVULN_FRAMES
                self.shake = 8
                self.heat = 0.0  # reset heat on hit
                self._spawn_explosion(e.x, e.y, 2, 3)  # yellow particles for hit
                self.texts.append(FloatingText(self.player_x, self.player_y - 10, "-1 HP", pyxel.COLOR_RED, 30))
                del self.enemies[ei]
                if self.hp <= 0:
                    self.phase = Phase.GAME_OVER
                    self.best_score = max(self.best_score, self.score)
                break

    def _update_particles(self) -> None:
        """Age particles; remove dead ones."""
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life > 0:
                p.x += p.vx
                p.y += p.vy
                p.vx *= 0.94
                p.vy *= 0.94
                alive.append(p)
        self.particles = alive

    def _update_texts(self) -> None:
        """Age floating texts; remove expired ones."""
        alive: list[FloatingText] = []
        for t in self.texts:
            t.life -= 1
            if t.life > 0:
                t.y -= 0.8
                alive.append(t)
        self.texts = alive

    def _update_overheat(self) -> None:
        """Overheat state: player stunned, heat rapidly decays."""
        self.overheat_timer -= 1
        if self.shake > 0:
            self.shake -= 1
        self.heat = max(0.0, self.heat - HEAT_OVERHEAT_DECAY)

        # Enemies keep moving and spawning during overheat
        self._update_enemies()
        self._spawn_enemies()
        self._check_player_hit()
        self._update_particles()
        self._update_texts()

        if self.overheat_timer <= 0:
            self.phase = Phase.PLAYING

    def _update_gameover(self) -> None:
        """Wait for restart input."""
        self._update_particles()
        self._update_texts()
        if self.shake > 0:
            self.shake -= 1
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    # ── Draw ──

    def draw(self) -> None:
        """Main draw loop, dispatched by phase."""
        pyxel.cls(pyxel.COLOR_BLACK)

        # Apply screen shake
        if self.shake > 0:
            shake_amt = max(1, self.shake // 3)
            ox = random.randint(-shake_amt, shake_amt)
            oy = random.randint(-shake_amt, shake_amt)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.OVERHEAT):
            self._draw_game_field()
            if self.phase == Phase.OVERHEAT:
                self._draw_overheat_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_field()
            self._draw_gameover_overlay()

    def _draw_title(self) -> None:
        """Title screen."""
        pyxel.text(WIDTH // 2 - 42, HEIGHT // 2 - 38, "CHAIN REACTOR", pyxel.COLOR_YELLOW)
        pyxel.text(WIDTH // 2 - 55, HEIGHT // 2 - 10, "Shoot same-color enemies", pyxel.COLOR_WHITE)
        pyxel.text(WIDTH // 2 - 50, HEIGHT // 2 + 2, "to trigger chain reactions!", pyxel.COLOR_WHITE)
        pyxel.text(WIDTH // 2 - 38, HEIGHT // 2 + 25, "WASD: Move", pyxel.COLOR_GRAY)
        pyxel.text(WIDTH // 2 - 42, HEIGHT // 2 + 35, "Mouse: Aim & Shoot", pyxel.COLOR_GRAY)
        pyxel.text(WIDTH // 2 - 50, HEIGHT // 2 + 50, "Don't overheat! (watch HEAT bar)", pyxel.COLOR_ORANGE)
        pyxel.text(WIDTH // 2 - 40, HEIGHT // 2 + 70, "SPACE or CLICK to start", pyxel.COLOR_LIME)
        if self.best_score > 0:
            msg = f"Best Score: {self.best_score}"
            pyxel.text(WIDTH // 2 - len(msg) * 2, HEIGHT // 2 + 85, msg, pyxel.COLOR_ORANGE)

    def _draw_game_field(self) -> None:
        """Draw all gameplay elements: enemies, bullets, player, effects, HUD."""
        # Particles (drawn first, behind everything)
        for p in self.particles:
            alpha = p.life / 22.0
            col = COLOR_PYXEL[p.color] if alpha > 0.4 else COLOR_DARK[p.color]
            if p.radius <= 2:
                pyxel.pset(int(p.x), int(p.y), col)
            else:
                pyxel.circ(int(p.x), int(p.y), p.radius, col)

        # Enemies
        for e in self.enemies:
            pyxel.circ(int(e.x), int(e.y), ENEMY_RADIUS, COLOR_PYXEL[e.color])
            pyxel.circ(int(e.x), int(e.y), ENEMY_RADIUS - 2, COLOR_DARK[e.color])

        # Bullets
        for b in self.bullets:
            pyxel.circ(int(b.x), int(b.y), BULLET_RADIUS, pyxel.COLOR_WHITE)
            pyxel.pset(int(b.x), int(b.y), pyxel.COLOR_YELLOW)

        # Player
        invuln_flash = self.invuln > 0 and (self.invuln // 6) % 2 == 0
        if not invuln_flash:
            px = int(self.player_x)
            py = int(self.player_y)
            pyxel.circ(px, py, PLAYER_RADIUS, pyxel.COLOR_WHITE)
            pyxel.circ(px, py, PLAYER_RADIUS - 2, pyxel.COLOR_CYAN)
            # Direction indicator (small triangle toward mouse)
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - self.player_x
            dy = my - self.player_y
            dist = math.hypot(dx, dy)
            if dist > 0:
                dx /= dist
                dy /= dist
                tx = int(self.player_x + dx * (PLAYER_RADIUS + 2))
                ty = int(self.player_y + dy * (PLAYER_RADIUS + 2))
                pyxel.pset(tx, ty, pyxel.COLOR_WHITE)

        # Floating texts
        for t in self.texts:
            alpha = t.life / 40.0
            col = t.color if alpha > 0.3 else pyxel.COLOR_GRAY
            x = int(t.x) - len(t.text) * 2
            pyxel.text(x, int(t.y), t.text, col)

        # Combo indicator (prominent, center-top)
        if self.combo > 1:
            combo_text = f"CHAIN x{self.combo}!"
            x = WIDTH // 2 - len(combo_text) * 2
            flash_col = pyxel.COLOR_YELLOW if self.frame % 12 < 6 else pyxel.COLOR_RED
            pyxel.text(x, 6, combo_text, flash_col)

        # HUD
        # Wave & Score (top-left)
        pyxel.text(4, 2, f"WAVE {self.wave}", pyxel.COLOR_WHITE)
        pyxel.text(4, 10, f"SCORE {self.score}", pyxel.COLOR_LIME)

        # HP (hearts, top-left below score)
        for i in range(self.hp):
            pyxel.circ(12 + i * 12, 24, 4, pyxel.COLOR_RED)
            pyxel.pset(12 + i * 12, 24, pyxel.COLOR_PINK)

        # Heat bar (top-right)
        bar_x = WIDTH - 54
        bar_y = 4
        bar_w = 50
        bar_h = 6
        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, pyxel.COLOR_GRAY)
        heat_w = int(bar_w * self.heat / MAX_HEAT)
        if self.heat < 40:
            hcol = pyxel.COLOR_LIME
        elif self.heat < 75:
            hcol = pyxel.COLOR_YELLOW
        else:
            hcol = pyxel.COLOR_RED
        pyxel.rect(bar_x, bar_y, heat_w, bar_h, hcol)
        pyxel.text(bar_x, bar_y + 8, "HEAT", pyxel.COLOR_GRAY)

        # Enemy count (below heat bar)
        ecount = f"E:{len(self.enemies)}"
        pyxel.text(bar_x, bar_y + 18, ecount, pyxel.COLOR_GRAY)

    def _draw_overheat_overlay(self) -> None:
        """Flash overlay during overheat state."""
        if self.frame % 10 < 5:
            msg = "OVERHEAT!"
            pyxel.text(WIDTH // 2 - 22, HEIGHT // 2 - 10, msg, pyxel.COLOR_RED)
            msg2 = "Can't shoot!"
            pyxel.text(WIDTH // 2 - 30, HEIGHT // 2 + 5, msg2, pyxel.COLOR_RED)

    def _draw_gameover_overlay(self) -> None:
        """Game over screen over the frozen game field."""
        # Dim the background with a semi-transparent rect
        pyxel.rect(0, 0, WIDTH, HEIGHT, pyxel.COLOR_BLACK)
        # Redraw key info
        pyxel.text(WIDTH // 2 - 25, HEIGHT // 2 - 40, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(WIDTH // 2 - 35, HEIGHT // 2 - 15, f"Score: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(WIDTH // 2 - 35, HEIGHT // 2 - 3, f"Wave: {self.wave}", pyxel.COLOR_WHITE)
        pyxel.text(WIDTH // 2 - 35, HEIGHT // 2 + 9, f"Kills: {self.kill_count}", pyxel.COLOR_WHITE)
        chain_msg = f"Max Chain: x{self.max_combo}"
        pyxel.text(WIDTH // 2 - len(chain_msg) * 2, HEIGHT // 2 + 22, chain_msg, pyxel.COLOR_YELLOW)
        if self.best_score > 0:
            best_msg = f"Best: {self.best_score}"
            pyxel.text(WIDTH // 2 - len(best_msg) * 2, HEIGHT // 2 + 38, best_msg, pyxel.COLOR_ORANGE)
        pyxel.text(WIDTH // 2 - 48, HEIGHT // 2 + 60, "SPACE or CLICK to retry", pyxel.COLOR_GRAY)


# ═══════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ChainReactor()
