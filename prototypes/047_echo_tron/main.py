"""ECHO TRON — Light cycle arena survival.

Reinterpreted from game_idea_factory idea #1 (score 32.55):
  - "log/replay as asset" → your movement trail becomes permanent arena walls
  - "CA grid fills up, must control" → trails fill the grid, constraining space

Core mechanic: Navigate a light cycle through a shrinking arena. Your trail
and enemy trails become walls. Collect same-color gems consecutively for
COMBO score multipliers. Trap enemies against walls to score kills.

Controls: Arrow keys to turn (can't reverse), SPACE to restart.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config ──

GRID_W = 30
GRID_H = 24
CELL = 8
PLAY_W = GRID_W * CELL  # 240
PLAY_H = GRID_H * CELL  # 192
HUD_H = 20
SCREEN_W = PLAY_W
SCREEN_H = PLAY_H + HUD_H

FPS = 60
TICK_BASE = 10  # frames per move at start (~6 moves/sec)
TICK_MIN = 4  # fastest (~15 moves/sec)
TICK_ACCEL = 0.02  # speedup per tick survived

NUM_ENEMIES = 3
NUM_GEMS = 6
NUM_COLORS = 4

# Module-level color indices to avoid TYPE_CHECKING pitfall
# 8=RED, 11=LIME, 12=CYAN, 9=ORANGE
COLOR_VALS: tuple[int, int, int, int] = (8, 11, 12, 9)

DIRS: tuple[tuple[int, int], ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))  # U R D L


# ── Data Classes ──


@dataclass
class Bike:
    """A light cycle in the arena."""

    x: int
    y: int
    d: int  # direction index 0-3
    alive: bool = True
    color: int = 0  # color index 0-3
    idx: int = -1  # wall_grid owner index (-1=player, 0+=enemy)


@dataclass
class Gem:
    """A collectible power gem."""

    x: int
    y: int
    color: int  # 0-3
    collected: bool = False


@dataclass
class Particle:
    """Visual particle for death/collect effects."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    max_life: int = 12


class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game ──


class Game:
    """ECHO TRON — Light cycle arena survival."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ECHO TRON", fps=FPS, display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all game state."""
        self._rng = random.Random()
        self.phase: Phase = Phase.PLAYING
        self.tick_timer: int = 0
        self.tick_interval: float = float(TICK_BASE)
        self.survived_ticks: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_color: int = -1  # -1 = no active combo
        self.kills: int = 0
        self._shake_frames: int = 0
        self._shake_intensity: int = 0

        # Wall grid: -1 = empty, 0 = player wall, 1+ = enemy wall
        self.wall_grid: list[list[int]] = [
            [-1 for _ in range(GRID_W)] for _ in range(GRID_H)
        ]

        # Bikes
        self.player: Bike = Bike(
            x=GRID_W // 4, y=GRID_H // 2, d=1, alive=True, color=0, idx=-1
        )
        self.enemies: list[Bike] = []
        self._spawn_enemies()

        # Gems
        self.gems: list[Gem] = []
        self._spawn_gems()

        # Particles
        self.particles: list[Particle] = []

    # ── Spawning ──

    def _spawn_enemies(self) -> None:
        """Spawn enemy bikes at edges facing inward."""
        spawns: list[tuple[int, int, int]] = [
            (GRID_W * 3 // 4, GRID_H // 4, 3),  # right side, facing left
            (GRID_W // 4, GRID_H * 3 // 4, 0),  # bottom, facing up
            (GRID_W * 3 // 4, GRID_H * 3 // 4, 2),  # right-bottom, facing down
        ]
        self.enemies.clear()
        for i, (sx, sy, sd) in enumerate(spawns[:NUM_ENEMIES]):
            self.enemies.append(
                Bike(x=sx, y=sy, d=sd, alive=True, color=(i + 1) % NUM_COLORS, idx=i + 1)
            )

    def _spawn_gems(self) -> None:
        """Spawn gems on random empty cells."""
        empty: list[tuple[int, int]] = self._find_empty_cells()
        self._rng.shuffle(empty)
        self.gems.clear()
        for i in range(min(NUM_GEMS, len(empty))):
            gx, gy = empty[i]
            self.gems.append(Gem(x=gx, y=gy, color=self._rng.randint(0, NUM_COLORS - 1)))

    def _find_empty_cells(self) -> list[tuple[int, int]]:
        """Return list of (x, y) cells that are empty (no wall, no bike)."""
        occupied: set[tuple[int, int]] = set()
        # Bikes are obstacles for gem placement
        if self.player.alive:
            occupied.add((self.player.x, self.player.y))
        for e in self.enemies:
            if e.alive:
                occupied.add((e.x, e.y))
        # Walls
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.wall_grid[y][x] >= 0:
                    occupied.add((x, y))

        result: list[tuple[int, int]] = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                if (x, y) not in occupied:
                    result.append((x, y))
        return result

    # ── Update ──

    def update(self) -> None:
        """Main update loop."""
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        # Handle input (queue direction changes)
        self._handle_input()

        # Tick timer
        self.tick_timer += 1
        if self.tick_timer >= int(self.tick_interval):
            self.tick_timer = 0
            self._tick()

        # Update particles
        self._update_particles()

        # Decrease shake
        if self._shake_frames > 0:
            self._shake_frames -= 1

    def _handle_input(self) -> None:
        """Queue direction changes from arrow keys. Can't reverse."""
        p = self.player
        if not p.alive:
            return
        new_d: int = -1
        if pyxel.btnp(pyxel.KEY_UP):
            new_d = 0
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            new_d = 1
        elif pyxel.btnp(pyxel.KEY_DOWN):
            new_d = 2
        elif pyxel.btnp(pyxel.KEY_LEFT):
            new_d = 3

        if new_d >= 0 and new_d != (p.d + 2) % 4:  # can't reverse
            p.d = new_d

    def _tick(self) -> None:
        """Process one game tick: move bikes, check collisions, spawn gems."""
        if self.phase != Phase.PLAYING:
            return

        self.survived_ticks += 1
        # Score for surviving
        self.score += 1

        # Speed up over time
        if self.tick_interval > TICK_MIN:
            self.tick_interval = max(TICK_MIN, self.tick_interval - TICK_ACCEL)

        # Enemy AI decides directions
        for e in self.enemies:
            if e.alive:
                self._ai_decide(e)

        # 1. All alive bikes compute next positions
        moves: dict[int, tuple[int, int]] = {}  # bike_idx → (nx, ny) or (-1, -1) if dead
        bike_indices: list[int] = []  # player=0, enemies=1..N

        for bi, bike in enumerate([self.player, *self.enemies]):
            if not bike.alive:
                moves[bi] = (-1, -1)
                continue
            bike_indices.append(bi)
            nx = bike.x + DIRS[bike.d][0]
            ny = bike.y + DIRS[bike.d][1]
            # Out of bounds check
            if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
                moves[bi] = (-1, -1)  # will die
            else:
                moves[bi] = (nx, ny)

        # 2. Check head-on collisions (two bikes targeting same cell)
        target_count: dict[tuple[int, int], list[int]] = {}
        for bi in bike_indices:
            tgt = moves[bi]
            if tgt != (-1, -1):
                target_count.setdefault(tgt, []).append(bi)

        dead_this_tick: set[int] = set()
        for tgt, bikers in target_count.items():
            if len(bikers) > 1:
                for bi in bikers:
                    dead_this_tick.add(bi)

        # 3. Place walls at all alive bikes' CURRENT positions
        for bi, bike in enumerate([self.player, *self.enemies]):
            if bike.alive and bi not in dead_this_tick:
                self.wall_grid[bike.y][bike.x] = max(0, bike.idx)

        # 4. Check wall collisions for remaining bikes
        for bi in bike_indices:
            if bi in dead_this_tick:
                continue
            nx, ny = moves[bi]
            if self.wall_grid[ny][nx] >= 0:
                dead_this_tick.add(bi)

        # 5. Move surviving bikes & collect gems (player only)
        for bi, bike in enumerate([self.player, *self.enemies]):
            if bi in dead_this_tick:
                if bike.alive:
                    self._kill_bike(bike)
                continue
            nx, ny = moves[bi]
            bike.x = nx
            bike.y = ny

        # Player gem collection
        if self.player.alive:
            self._check_gem_collection()

        # Spawn new gems if needed (keep NUM_GEMS on field)
        active_gems = sum(1 for g in self.gems if not g.collected)
        if active_gems < NUM_GEMS:
            self._spawn_gem_single()
            self._spawn_gem_single()

        # Spawn new gems occasionally
        if self.survived_ticks % 30 == 0 and active_gems < NUM_GEMS + 2:
            self._spawn_gem_single()

        # Win check: all enemies dead
        alive_enemies = sum(1 for e in self.enemies if e.alive)
        if alive_enemies == 0:
            max_bonus = self.max_combo * 50
            self.score += 200 + max_bonus
            self._add_particles(self.player.x * CELL + CELL // 2,
                                self.player.y * CELL + CELL // 2,
                                30, self.player.color)
            self.phase = Phase.GAME_OVER

    def _kill_bike(self, bike: Bike) -> None:
        """Mark a bike as dead and spawn death particles."""
        bike.alive = False
        px = bike.x * CELL + CELL // 2
        py = bike.y * CELL + CELL // 2
        self._add_particles(px, py, 20, bike.color)
        self._shake_frames = 8
        self._shake_intensity = 3

        if bike.idx < 0:  # player
            self.score += self.max_combo * 20
            self.phase = Phase.GAME_OVER
        else:
            self.kills += 1
            self.score += 100 + self.combo * 20

    def _check_gem_collection(self) -> None:
        """Check if player collected any gems at their current position."""
        px, py = self.player.x, self.player.y
        for g in self.gems:
            if g.collected:
                continue
            if g.x == px and g.y == py:
                g.collected = True
                self._add_particles(
                    px * CELL + CELL // 2, py * CELL + CELL // 2, 8, g.color
                )
                # COMBO logic
                if g.color == self.combo_color:
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.score += 10 * self.combo
                    self.player.color = g.color
                else:
                    self.combo = 1
                    self.combo_color = g.color
                    self.player.color = g.color
                    self.score += 10
                break

    def _spawn_gem_single(self) -> None:
        """Spawn one gem on a random empty cell."""
        empty = self._find_empty_cells()
        if not empty:
            return
        gx, gy = self._rng.choice(empty)
        self.gems.append(Gem(x=gx, y=gy, color=self._rng.randint(0, NUM_COLORS - 1)))

    # ── Particles ──

    def _add_particles(self, cx: float, cy: float, count: int, color: int) -> None:
        """Spawn particle burst at (cx, cy)."""
        col_val = COLOR_VALS[color]
        for _ in range(count):
            angle = self._rng.random() * 6.2832
            speed = self._rng.random() * 2.0 + 0.5
            life = self._rng.randint(8, 18)
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    max_life=life,
                    color=col_val,
                )
            )

    def _update_particles(self) -> None:
        """Update particle positions and remove dead ones."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Enemy AI ──

    def _ai_decide(self, enemy: Bike) -> None:
        """Decide enemy's next direction (called before each tick)."""
        # Get valid directions (not reverse)
        reverse = (enemy.d + 2) % 4
        options: list[tuple[int, int]] = []
        for turn in (-1, 0, 1):
            nd = (enemy.d + turn) % 4
            if nd == reverse:
                continue
            nx = enemy.x + DIRS[nd][0]
            ny = enemy.y + DIRS[nd][1]
            if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
                continue
            if self.wall_grid[ny][nx] >= 0:
                continue
            options.append((nd, self._count_open(nx, ny, nd)))

        if not options:
            # No good options — try any non-reverse direction even if wall
            for turn in (-1, 0, 1):
                nd = (enemy.d + turn) % 4
                if nd != reverse:
                    enemy.d = nd
                    return
            enemy.d = reverse  # last resort
            return

        # Sort by open space (descending)
        options.sort(key=lambda x: x[1], reverse=True)
        # Pick from top options with some randomness
        best_space = options[0][1]
        top = [(nd, s) for nd, s in options if s >= best_space - 3]
        nd, _s = self._rng.choice(top)
        enemy.d = nd

    def _count_open(self, sx: int, sy: int, d: int, max_depth: int = 8) -> int:
        """Count consecutive open cells in a direction (ray cast)."""
        count = 0
        dx, dy = DIRS[d]
        cx, cy = sx, sy
        for _ in range(max_depth):
            if cx < 0 or cx >= GRID_W or cy < 0 or cy >= GRID_H:
                break
            if self.wall_grid[cy][cx] >= 0:
                break
            count += 1
            cx += dx
            cy += dy
        # Also check side openness
        side_count = 0
        for turn in (-1, 1):
            sd = (d + turn) % 4
            sdx, sdy = DIRS[sd]
            scx, scy = sx + sdx, sy + sdy
            if 0 <= scx < GRID_W and 0 <= scy < GRID_H and self.wall_grid[scy][scx] < 0:
                side_count += 1
        return count + side_count

    # ── Draw ──

    def draw(self) -> None:
        """Render the game."""
        pyxel.cls(pyxel.COLOR_BLACK)

        # Screen shake offset
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-self._shake_intensity, self._shake_intensity)
            shake_y = self._rng.randint(-self._shake_intensity, self._shake_intensity)

        # Draw walls
        for y in range(GRID_H):
            for x in range(GRID_W):
                widx = self.wall_grid[y][x]
                if widx >= 0:
                    sx = x * CELL + shake_x
                    sy = y * CELL + shake_y
                    if widx == 0:  # player wall
                        col = COLOR_VALS[self.player.color]
                    else:
                        col = COLOR_VALS[(widx - 1) % NUM_COLORS]
                    pyxel.rect(sx, sy, CELL, CELL, col)

        # Draw gems
        for g in self.gems:
            if g.collected:
                continue
            gx = g.x * CELL + CELL // 2 + shake_x
            gy = g.y * CELL + CELL // 2 + shake_y
            col = COLOR_VALS[g.color]
            # Gem diamond shape
            pyxel.rect(gx - 2, gy - 2, 4, 4, col)
            pyxel.pset(gx, gy - 3, pyxel.COLOR_WHITE)
            pyxel.pset(gx, gy + 3, pyxel.COLOR_WHITE)
            pyxel.pset(gx - 3, gy, pyxel.COLOR_WHITE)
            pyxel.pset(gx + 3, gy, pyxel.COLOR_WHITE)

        # Draw enemies
        for e in self.enemies:
            if not e.alive:
                continue
            ex = e.x * CELL + CELL // 2 + shake_x
            ey = e.y * CELL + CELL // 2 + shake_y
            col = COLOR_VALS[e.color]
            # Enemy bike: filled square with direction indicator
            pyxel.rect(ex - 3, ey - 3, 6, 6, col)
            # Direction arrow
            adx, ady = DIRS[e.d]
            pyxel.rect(ex + adx * 3 - 1, ey + ady * 3 - 1, 2, 2, pyxel.COLOR_WHITE)

        # Draw player
        if self.player.alive:
            px = self.player.x * CELL + CELL // 2 + shake_x
            py = self.player.y * CELL + CELL // 2 + shake_y
            col = COLOR_VALS[self.player.color]
            # Player bike: larger square with glow
            pyxel.rect(px - 4, py - 4, 8, 8, pyxel.COLOR_BLACK)
            pyxel.rectb(px - 4, py - 4, 8, 8, col)
            pyxel.rect(px - 2, py - 2, 4, 4, col)
            # Direction indicator
            adx, ady = DIRS[self.player.d]
            pyxel.rect(px + adx * 4 - 1, py + ady * 4 - 1, 2, 2, pyxel.COLOR_WHITE)

        # Draw particles
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            if alpha > 0.5:
                col = p.color
            elif alpha > 0.2:
                col = pyxel.COLOR_GRAY
            else:
                col = pyxel.COLOR_NAVY
            px_s = int(p.x) + shake_x
            py_s = int(p.y) + shake_y
            pyxel.pset(px_s, py_s, col)

        # ── HUD ──
        hud_y = PLAY_H + 2
        # Score
        pyxel.text(2, hud_y, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)
        # Combo
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(90, hud_y, combo_text, COLOR_VALS[self.combo_color % NUM_COLORS] if self.combo_color >= 0 else pyxel.COLOR_WHITE)
        # Speed
        speed_pct = int((1.0 - (self.tick_interval - TICK_MIN) / (TICK_BASE - TICK_MIN)) * 100)
        pyxel.text(160, hud_y, f"SPD:{speed_pct:03d}%", pyxel.COLOR_GRAY)
        # Kills
        pyxel.text(210, hud_y, f"K:{self.kills}", pyxel.COLOR_ORANGE)

        # ── Game Over screen ──
        if self.phase == Phase.GAME_OVER:
            # Dim overlay
            for y in range(0, PLAY_H, 4):
                for x in range(0, PLAY_W, 4):
                    if (x // 4 + y // 4) % 2 == 0:
                        pyxel.pset(x, y, pyxel.COLOR_NAVY)

            # Game over text
            msg = "GAME OVER"
            tx = (PLAY_W - len(msg) * 4) // 2
            pyxel.text(tx, PLAY_H // 2 - 12, msg, pyxel.COLOR_RED)
            # Final score
            score_msg = f"SCORE: {self.score}"
            sx = (PLAY_W - len(score_msg) * 4) // 2
            pyxel.text(sx, PLAY_H // 2, score_msg, pyxel.COLOR_WHITE)
            # Max combo
            combo_msg = f"MAX COMBO: x{self.max_combo}"
            cx = (PLAY_W - len(combo_msg) * 4) // 2
            pyxel.text(cx, PLAY_H // 2 + 8, combo_msg, pyxel.COLOR_YELLOW)
            # Restart
            restart_msg = "SPACE to restart"
            rx = (PLAY_W - len(restart_msg) * 4) // 2
            pyxel.text(rx, PLAY_H // 2 + 20, restart_msg, pyxel.COLOR_GRAY)


# ── Entry point ──

if __name__ == "__main__":
    Game()
