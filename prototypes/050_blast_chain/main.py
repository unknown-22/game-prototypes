"""Blast Chain — Bomberman-style grid action with color-chain explosions.

Core mechanic: Place bombs on a grid. Same-color bomb explosions chain-react
to clear enemies and score combos. Risk: don't get caught in your own blasts.

Genre: Bomberman-like / grid action (NEW to the collection)
Reinterpreted from: Idea #1 Score 31.95 (dice/bag roguelite, logistics/flow)
Transfer hooks: "synthesis compression" → same-color chain reaction
                "circuit/pipe visualization" → chain blast propagation
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Constants ──
SCREEN_W = 256
SCREEN_H = 200
GRID_OX = 32
GRID_OY = 24
CELL = 16
GRID_COLS = 12
GRID_ROWS = 10
PLAY_W = GRID_COLS * CELL
PLAY_H = GRID_ROWS * CELL

# Bomb colors: RED, GREEN, DARK_BLUE, YELLOW, PURPLE (pyxel ints)
BOMB_COLORS: tuple[int, ...] = (8, 11, 5, 10, 2)
NUM_COLORS: int = len(BOMB_COLORS)

BOMB_FUSE: int = 90
EXPLOSION_DURATION: int = 20
CHAIN_DELAY: int = 8
BLAST_RADIUS: float = CELL * 1.0
CHAIN_BLAST_RADIUS: float = CELL * 1.5
PLAYER_MOVE_SPEED: float = 2.0
ENEMY_BASE_SPEED: float = 1.0
ENEMY_SPEED_PER_WAVE: float = 0.25
PARTICLE_COUNT: int = 8
PARTICLE_LIFE: int = 15
BOMB_LIMIT: int = 3
BOMB_COOLDOWN: int = 12
STARTING_LIVES: int = 3
BASE_ENEMIES: int = 3
ENEMIES_PER_WAVE: int = 1
MAX_ENEMIES: int = 10
WAVE_CLEAR_PAUSE: int = 45
DEATH_PAUSE: int = 40
ENEMY_COLOR: int = 6  # LIGHT_BLUE
PLAYER_COLOR: int = 3  # GREEN
EXPLOSION_COLOR: int = 9  # ORANGE
HUD_BG: int = 1  # NAVY


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    CHAINING = auto()
    DYING = auto()
    WAVE_CLEAR = auto()
    GAME_OVER = auto()


@dataclass
class Bomb:
    gx: int
    gy: int
    color: int
    timer: int = BOMB_FUSE
    chained: bool = False


@dataclass
class Enemy:
    x: float
    y: float
    speed: float
    move_timer: float = 0.0
    direction: int = 0


@dataclass
class Explosion:
    x: float
    y: float
    timer: int = EXPLOSION_DURATION
    radius: float = BLAST_RADIUS
    color: int = 9  # ORANGE


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    """Bomberman-style grid action with color-chain explosions."""

    DIRECTIONS: ClassVar[list[tuple[int, int]]] = [
        (0, -1), (1, 0), (0, 1), (-1, 0),
    ]

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Blast Chain", display_scale=3)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_x: float = GRID_OX + PLAY_W / 2
        self.player_y: float = GRID_OY + PLAY_H / 2
        self.lives: int = STARTING_LIVES
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.wave: int = 0
        self.bombs: list[Bomb] = []
        self.enemies: list[Enemy] = []
        self.explosions: list[Explosion] = []
        self.particles: list[Particle] = []
        self._bomb_cooldown: int = 0
        self._chain_queue: list[Bomb] = []
        self._chain_timer: int = 0
        self._pause_timer: int = 0
        self._can_chain: bool = True

    # ── Coordinate helpers ──

    def _grid_to_pixel(self, gx: int, gy: int) -> tuple[float, float]:
        return (
            GRID_OX + gx * CELL + CELL / 2,
            GRID_OY + gy * CELL + CELL / 2,
        )

    def _pixel_to_grid(self, px: float, py: float) -> tuple[int, int]:
        return (int((px - GRID_OX) / CELL), int((py - GRID_OY) / CELL))

    def _bomb_at(self, gx: int, gy: int) -> Bomb | None:
        for b in self.bombs:
            if b.gx == gx and b.gy == gy:
                return b
        return None

    def _in_bounds(self, gx: int, gy: int) -> bool:
        return 0 <= gx < GRID_COLS and 0 <= gy < GRID_ROWS

    # ── Wave management ──

    def _spawn_enemies(self, count: int) -> None:
        pgx, pgy = self._pixel_to_grid(self.player_x, self.player_y)
        for _ in range(count):
            gx = self._rng.randint(0, GRID_COLS - 1)
            gy = self._rng.randint(0, GRID_ROWS - 1)
            for _ in range(50):  # try up to 50 times
                dist = abs(gx - pgx) + abs(gy - pgy)
                if dist >= 3 and self._bomb_at(gx, gy) is None:
                    break
                gx = self._rng.randint(0, GRID_COLS - 1)
                gy = self._rng.randint(0, GRID_ROWS - 1)
            px, py = self._grid_to_pixel(gx, gy)
            speed = ENEMY_BASE_SPEED + self.wave * ENEMY_SPEED_PER_WAVE
            self.enemies.append(Enemy(px, py, speed))

    def _start_wave(self) -> None:
        self.wave += 1
        count = min(BASE_ENEMIES + (self.wave - 1) * ENEMIES_PER_WAVE, MAX_ENEMIES)
        self._spawn_enemies(count)

    # ── Player actions ──

    def _place_bomb(self) -> None:
        gx, gy = self._pixel_to_grid(self.player_x, self.player_y)
        if not self._in_bounds(gx, gy):
            return
        if self._bomb_at(gx, gy) is not None:
            return
        if len(self.bombs) >= BOMB_LIMIT:
            return
        color = self._rng.randint(0, NUM_COLORS - 1)
        self.bombs.append(Bomb(gx, gy, color))
        self._bomb_cooldown = BOMB_COOLDOWN

    def _kill_player(self) -> None:
        self.lives -= 1
        self.phase = Phase.DYING
        self._pause_timer = DEATH_PAUSE
        self.combo = 0
        # spawn death particles
        for _ in range(12):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.5, 3.5)
            self.particles.append(Particle(
                self.player_x, self.player_y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                PARTICLE_LIFE + 5,
                8,  # RED
            ))

    # ── Explosion & chain logic ──

    def _detonate_bomb(self, bomb: Bomb, is_chain: bool = False) -> None:
        px, py = self._grid_to_pixel(bomb.gx, bomb.gy)
        radius = CHAIN_BLAST_RADIUS if is_chain else BLAST_RADIUS
        self.explosions.append(Explosion(px, py, EXPLOSION_DURATION, radius))

        # Find same-color bombs in blast radius for chain
        chain_hits = 0
        for other in self.bombs:
            if other is bomb or other.chained:
                continue
            ox, oy = self._grid_to_pixel(other.gx, other.gy)
            dist = math.hypot(ox - px, oy - py)
            if dist <= radius:
                if other.color == bomb.color:
                    other.chained = True
                    other.timer = 0  # detonate immediately via chain
                    self._chain_queue.append(other)
                    chain_hits += 1
                else:
                    # Different color: detonate but no combo
                    other.chained = True
                    other.timer = 0
                    self._chain_queue.append(other)

        if chain_hits > 0:
            self.combo += chain_hits
            self.max_combo = max(self.max_combo, self.combo)
            if self.phase == Phase.PLAYING:
                self.phase = Phase.CHAINING
                self._chain_timer = CHAIN_DELAY

        # Kill enemies in blast
        for enemy in self.enemies[:]:
            dist = math.hypot(enemy.x - px, enemy.y - py)
            if dist < radius:
                self.enemies.remove(enemy)
                pts = (10 + self.combo * 8) * max(1, self.combo // 2 + 1)
                self.score += pts
                self._spawn_particles(enemy.x, enemy.y, bomb.color)

        # Kill player?
        pdist = math.hypot(self.player_x - px, self.player_y - py)
        if pdist < radius * 0.85 and self.phase in (Phase.PLAYING, Phase.CHAINING):
            self._kill_player()

        # Remove bomb
        if bomb in self.bombs:
            self.bombs.remove(bomb)

    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(PARTICLE_COUNT):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 3.5)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                PARTICLE_LIFE + self._rng.randint(-4, 2),
                color,
            ))

    # ── Update methods ──

    def _update_player(self) -> None:
        if self.phase not in (Phase.PLAYING, Phase.CHAINING):
            return
        dx: float = 0.0
        dy: float = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_MOVE_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_MOVE_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_MOVE_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_MOVE_SPEED
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
        nx = self.player_x + dx
        ny = self.player_y + dy
        # Clamp within play area
        nx = max(GRID_OX + 4, min(GRID_OX + PLAY_W - 5, nx))
        ny = max(GRID_OY + 4, min(GRID_OY + PLAY_H - 5, ny))
        # Check bomb collision: avoid walking through a bomb's cell
        gx, gy = self._pixel_to_grid(nx, ny)
        if self._bomb_at(gx, gy) is None:
            self.player_x = nx
            self.player_y = ny
        else:
            # Allow partial movement (slide along bomb edges)
            # Try horizontal only
            hx = max(GRID_OX + 4, min(GRID_OX + PLAY_W - 5, self.player_x + dx))
            hgx, _ = self._pixel_to_grid(hx, self.player_y)
            if self._bomb_at(hgx, gy) is None:
                self.player_x = hx
            # Try vertical only
            vy = max(GRID_OY + 4, min(GRID_OY + PLAY_H - 5, self.player_y + dy))
            _, vgy = self._pixel_to_grid(self.player_x, vy)
            if self._bomb_at(gx, vgy) is None:
                self.player_y = vy

        if self._bomb_cooldown > 0:
            self._bomb_cooldown -= 1
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_X):
            self._place_bomb()

    def _update_bombs(self) -> None:
        for bomb in self.bombs[:]:
            if bomb.chained:
                continue
            bomb.timer -= 1
            if bomb.timer <= 0:
                self.combo = 0
                self._detonate_bomb(bomb, is_chain=False)

    def _update_chain(self) -> None:
        if self.phase != Phase.CHAINING:
            return
        self._chain_timer -= 1
        if self._chain_timer <= 0 and self._chain_queue:
            next_bomb = self._chain_queue.pop(0)
            if next_bomb in self.bombs:
                self._detonate_bomb(next_bomb, is_chain=True)
            self._chain_timer = CHAIN_DELAY
        if not self._chain_queue and self._chain_timer <= 0:
            self._chain_timer = 10  # brief cooldown before returning to PLAYING
            if not self._chain_queue:
                self._chain_timer = 0
                self.phase = Phase.PLAYING
                self.combo = 0

    def _update_enemies(self) -> None:
        if self.phase not in (Phase.PLAYING, Phase.CHAINING):
            return
        for enemy in self.enemies:
            enemy.move_timer -= 1
            if enemy.move_timer <= 0:
                enemy.move_timer = self._rng.uniform(8, 25) / (0.5 + enemy.speed)
                enemy.direction = self._rng.randint(0, 3)
            dx, dy = 0.0, 0.0
            if enemy.direction == 0:
                dx = enemy.speed
            elif enemy.direction == 1:
                dy = enemy.speed
            elif enemy.direction == 2:
                dx = -enemy.speed
            else:
                dy = -enemy.speed
            enemy.x = max(GRID_OX + 4, min(GRID_OX + PLAY_W - 5, enemy.x + dx))
            enemy.y = max(GRID_OY + 4, min(GRID_OY + PLAY_H - 5, enemy.y + dy))
            # Collision with player
            if self.phase in (Phase.PLAYING, Phase.CHAINING):
                dist = math.hypot(enemy.x - self.player_x, enemy.y - self.player_y)
                if dist < 10:
                    self._kill_player()
                    return

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # slight gravity
            if p.life <= 0:
                self.particles.remove(p)

    def _update_explosions(self) -> None:
        for exp in self.explosions[:]:
            exp.timer -= 1
            if exp.timer <= 0:
                self.explosions.remove(exp)

    def update(self) -> None:
        # TITLE
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self._start_wave()
            return

        # GAME_OVER
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.PLAYING
                self._start_wave()
            return

        # DYING
        if self.phase == Phase.DYING:
            self._update_particles()
            self._update_explosions()
            self._pause_timer -= 1
            if self._pause_timer <= 0:
                if self.lives <= 0:
                    self.phase = Phase.GAME_OVER
                else:
                    self.player_x = GRID_OX + PLAY_W / 2
                    self.player_y = GRID_OY + PLAY_H / 2
                    self.bombs.clear()
                    self._chain_queue.clear()
                    self.explosions.clear()
                    self.phase = Phase.PLAYING
            return

        # WAVE_CLEAR
        if self.phase == Phase.WAVE_CLEAR:
            self._update_particles()
            self._pause_timer -= 1
            if self._pause_timer <= 0:
                self._start_wave()
                self.phase = Phase.PLAYING
            return

        # PLAYING or CHAINING
        self._update_player()
        self._update_bombs()
        self._update_chain()
        self._update_enemies()
        self._update_particles()
        self._update_explosions()

        # Check wave clear AFTER enemy updates (in case enemies died this frame)
        if self.phase in (Phase.PLAYING, Phase.CHAINING) and not self.enemies and not self._chain_queue:
            self.phase = Phase.WAVE_CLEAR
            self._pause_timer = WAVE_CLEAR_PAUSE
            self.score += 50 * self.wave
            self.combo = 0

    # ── Draw methods ──

    def draw(self) -> None:
        pyxel.cls(0)

        # Play area border
        pyxel.rectb(GRID_OX - 1, GRID_OY - 1, PLAY_W + 2, PLAY_H + 2, 5)

        # Grid lines (subtle)
        for i in range(GRID_COLS + 1):
            x = GRID_OX + i * CELL
            pyxel.line(x, GRID_OY, x, GRID_OY + PLAY_H, 13)
        for i in range(GRID_ROWS + 1):
            y = GRID_OY + i * CELL
            pyxel.line(GRID_OX, y, GRID_OX + PLAY_W, y, 13)

        # Bombs
        for bomb in self.bombs:
            px, py = self._grid_to_pixel(bomb.gx, bomb.gy)
            r = CELL // 2 - 3
            col = BOMB_COLORS[bomb.color]
            pyxel.circ(px, py, r, col)
            pyxel.circb(px, py, r, 7)
            # Fuse blink (last 30 frames)
            if bomb.timer < 30 and (bomb.timer // 4) % 2 == 0:
                pyxel.circb(px, py, r + 1, 7)
            # Chain marker
            if bomb.chained:
                pyxel.text(px - 2, py - 3, ">", 7)

        # Explosions
        for exp in self.explosions:
            t = 1.0 - exp.timer / EXPLOSION_DURATION
            r = exp.radius * (0.3 + 0.7 * t)
            # Outer ring
            pyxel.circb(exp.x, exp.y, r, 9 if t < 0.6 else 8)
            # Inner fill
            pyxel.circ(exp.x, exp.y, r * 0.5, 10 if t < 0.5 else 9)

        # Enemies
        for enemy in self.enemies:
            ex, ey = int(enemy.x), int(enemy.y)
            pyxel.rect(ex - 5, ey - 5, 10, 10, ENEMY_COLOR)
            pyxel.rectb(ex - 5, ey - 5, 10, 10, 7)
            # Eyes
            pyxel.pset(ex - 2, ey - 2, 0)
            pyxel.pset(ex + 2, ey - 2, 0)

        # Player
        if self.phase != Phase.DYING or (self._pause_timer // 3) % 2 == 0:
            px, py = int(self.player_x), int(self.player_y)
            pyxel.rect(px - 5, py - 5, 10, 10, PLAYER_COLOR)
            pyxel.rectb(px - 5, py - 5, 10, 10, 7)
            # Face
            pyxel.pset(px - 2, py - 2, 7)
            pyxel.pset(px + 2, py - 2, 7)
            pyxel.line(px - 2, py + 1, px + 2, py + 1, 7)

        # Particles
        for p in self.particles:
            alpha = p.life / (PARTICLE_LIFE + 5)
            col = p.color if alpha > 0.4 else 7
            pyxel.pset(int(p.x), int(p.y), col)

        # HUD
        pyxel.rect(0, 0, SCREEN_W, 22, HUD_BG)
        pyxel.text(2, 2, f"SCORE:{self.score:05d}", 7)
        pyxel.text(2, 12, f"WAVE:{self.wave}", 7)
        pyxel.text(72, 2, f"LIVES:{'*' * self.lives}", 8)
        combo_color = 10 if self.combo >= 5 else 9 if self.combo >= 3 else 7
        pyxel.text(72, 12, f"COMBO:{self.combo}", combo_color)
        pyxel.text(142, 2, f"MAX:{self.max_combo}", 7)

        # Color legend (bottom-right)
        for i in range(NUM_COLORS):
            x = SCREEN_W - 55 + i * 11
            pyxel.rect(x, 2, 5, 5, BOMB_COLORS[i])

        # Phase overlays
        if self.phase == Phase.TITLE:
            self._draw_centered_text("BLAST CHAIN", SCREEN_H // 2 - 20, 7)
            self._draw_centered_text("SPACE to start", SCREEN_H // 2 + 2, 6)
            self._draw_centered_text("Same-color bombs = CHAIN!", SCREEN_H // 2 + 18, 5)
        elif self.phase == Phase.GAME_OVER:
            pyxel.rect(SCREEN_W // 2 - 55, SCREEN_H // 2 - 22, 110, 44, 0)
            pyxel.rectb(SCREEN_W // 2 - 55, SCREEN_H // 2 - 22, 110, 44, 8)
            self._draw_centered_text("GAME OVER", SCREEN_H // 2 - 12, 8)
            self._draw_centered_text(f"Wave:{self.wave} Score:{self.score}", SCREEN_H // 2, 7)
            self._draw_centered_text("SPACE to retry", SCREEN_H // 2 + 12, 6)
        elif self.phase == Phase.WAVE_CLEAR:
            self._draw_centered_text(f"WAVE {self.wave} CLEAR!", SCREEN_H // 2, 10)
        elif self.combo >= 3:
            c = 10 if self.combo >= 5 else 9
            self._draw_centered_text(f"CHAIN x{self.combo}!", SCREEN_H - 14, c)

    def _draw_centered_text(self, text: str, y: int, color: int) -> None:
        x = SCREEN_W // 2 - len(text) * 2
        pyxel.text(x, y, text, color)


if __name__ == "__main__":
    Game()
