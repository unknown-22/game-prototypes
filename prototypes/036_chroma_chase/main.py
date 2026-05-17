"""
CHROMA CHASE — Color-match maze chase
======================================
Reinterpreted from game idea #1 (score 32.15):
  Hook A "log/replay as asset" → player trail becomes a defensive weapon
  Hook B "CA grid spread"       → ghosts multiply across the grid over time
Genre: Maze Chase (Pac-Man-like) — first in collection

Core mechanic: Eat same-colored gems consecutively to build COMBO.
Your movement trail damages ghosts when COMBO >= 2.
Ghosts multiply. Greed for combo vs. safety.

Source idea: ダイス/バッグ構築ローグライト / 魔法学院（ルール改変）
  Score 32.15, hooks: log/replay as asset + CA grid spread control
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config ──
SCREEN_W = 256
SCREEN_H = 256
CELL = 16
GRID_W = SCREEN_W // CELL  # 16
GRID_H = SCREEN_H // CELL  # 16
NUM_COLORS = 5
FPS = 30

PLAYER_MOVE_DELAY = 4
GHOST_MOVE_DELAY = 8
GHOST_SPAWN_INTERVAL = 600  # 20 seconds
MAX_GEMS = 8
INVINCIBLE_DURATION = 180  # 6 seconds
TRAIL_DURATION = 360  # 12 seconds
POWER_GEM_CHANCE = 0.12
INITIAL_GHOSTS = 2
OBSTACLE_COUNT = 10

# Pyxel color palettes (only the 16 defined constants)
PX_COLORS: list[int] = [
    pyxel.COLOR_RED,        # 0
    pyxel.COLOR_LIGHT_BLUE, # 1
    pyxel.COLOR_GREEN,      # 2
    pyxel.COLOR_YELLOW,     # 3
    pyxel.COLOR_PURPLE,     # 4
]
PX_DARK: list[int] = [
    pyxel.COLOR_BROWN,      # 0
    pyxel.COLOR_DARK_BLUE,  # 1
    pyxel.COLOR_LIME,       # 2
    pyxel.COLOR_ORANGE,     # 3
    pyxel.COLOR_PINK,       # 4
]


# ── Data Classes ──
@dataclass
class Ghost:
    x: int
    y: int


@dataclass
class Gem:
    x: int
    y: int
    color: int  # -1 = power gem, 0-4 = element colors


@dataclass
class TrailCell:
    x: int
    y: int
    color: int
    life: int


@dataclass
class FloatingText:
    x: int
    y: int
    text: str
    color: int
    life: int


# ── Phase Enum ──
class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game ──
class Game:
    """Top-level Pyxel game class. Handles update/draw loop and state."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA CHASE", fps=FPS)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Initialize or reset all game state to starting conditions."""
        self.phase = Phase.PLAYING
        self.player_x: int = GRID_W // 2
        self.player_y: int = GRID_H // 2
        self.player_color: int = -1
        self.player_cooldown: int = 0
        self.ghosts: list[Ghost] = []
        self.gems: list[Gem] = []
        self.trails: list[TrailCell] = []
        self.texts: list[FloatingText] = []
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.gems_eaten: int = 0
        self.invincible_timer: int = 0
        self.ghost_spawn_timer: int = GHOST_SPAWN_INTERVAL
        self.ghost_cooldown: int = 0
        self.frame: int = 0
        self._obstacles: set[tuple[int, int]] = set()
        self._rng: random.Random = random.Random()

        self._generate_obstacles()
        for _ in range(INITIAL_GHOSTS):
            self._spawn_ghost()
        for _ in range(MAX_GEMS):
            self._spawn_gem()

    # ── Grid Helpers ──

    def _is_blocked(self, x: int, y: int) -> bool:
        """Return True if the cell is outside bounds or an obstacle."""
        if x < 0 or x >= GRID_W or y < 0 or y >= GRID_H:
            return True
        return (x, y) in self._obstacles

    def _has_trail_at(self, x: int, y: int) -> bool:
        """Check if there's a trail cell at the given position."""
        return any(t.x == x and t.y == y for t in self.trails)

    def _random_empty_cell(self) -> tuple[int, int]:
        """Find a random unblocked cell not occupied by player, ghost, or gem."""
        for _ in range(200):
            cx = self._rng.randint(0, GRID_W - 1)
            cy = self._rng.randint(0, GRID_H - 1)
            if self._is_blocked(cx, cy):
                continue
            if cx == self.player_x and cy == self.player_y:
                continue
            if any(g.x == cx and g.y == cy for g in self.ghosts):
                continue
            if any(g.x == cx and g.y == cy for g in self.gems):
                continue
            return cx, cy
        # Fallback: scan the grid
        for cx in range(GRID_W):
            for cy in range(GRID_H):
                if self._is_blocked(cx, cy):
                    continue
                if cx == self.player_x and cy == self.player_y:
                    continue
                if any(g.x == cx and g.y == cy for g in self.ghosts):
                    continue
                if any(g.x == cx and g.y == cy for g in self.gems):
                    continue
                return cx, cy
        return 0, 0

    def _generate_obstacles(self) -> None:
        """Place fixed obstacles on the grid (deterministic for reproducibility)."""
        seed_rng = random.Random(42)
        for _ in range(OBSTACLE_COUNT * 3):
            ox = seed_rng.randint(1, GRID_W - 2)
            oy = seed_rng.randint(1, GRID_H - 2)
            if (ox, oy) == (GRID_W // 2, GRID_H // 2):
                continue
            self._obstacles.add((ox, oy))
            if len(self._obstacles) >= OBSTACLE_COUNT:
                break

    # ── Spawning ──

    def _spawn_ghost(self) -> None:
        """Spawn a ghost at a random edge cell away from the player."""
        for _ in range(100):
            side = self._rng.randint(0, 3)
            if side == 0:
                gx, gy = self._rng.randint(0, GRID_W - 1), 0
            elif side == 1:
                gx, gy = self._rng.randint(0, GRID_W - 1), GRID_H - 1
            elif side == 2:
                gx, gy = 0, self._rng.randint(0, GRID_H - 1)
            else:
                gx, gy = GRID_W - 1, self._rng.randint(0, GRID_H - 1)
            if self._is_blocked(gx, gy):
                continue
            dist = abs(gx - self.player_x) + abs(gy - self.player_y)
            if dist >= 4:
                self.ghosts.append(Ghost(gx, gy))
                return
        # Fallback: any empty cell
        cx, cy = self._random_empty_cell()
        self.ghosts.append(Ghost(cx, cy))

    def _spawn_gem(self) -> None:
        """Spawn a colored gem (or power gem) on a random empty cell."""
        cx, cy = self._random_empty_cell()
        if self._rng.random() < POWER_GEM_CHANCE:
            color = -1
        else:
            color = self._rng.randint(0, NUM_COLORS - 1)
        self.gems.append(Gem(cx, cy, color))

    # ── Player ──

    def _update_player(self) -> None:
        """Handle player input and grid movement."""
        if self.player_cooldown > 0:
            self.player_cooldown -= 1
            return

        dx, dy = 0, 0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -1
        elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = 1
        elif pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -1
        elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = 1

        if dx == 0 and dy == 0:
            return

        nx = self.player_x + dx
        ny = self.player_y + dy
        if self._is_blocked(nx, ny):
            return

        # Leave trail on current cell before moving
        if self.combo >= 2:
            self.trails.append(
                TrailCell(self.player_x, self.player_y, self.player_color, TRAIL_DURATION)
            )
        self.player_x = nx
        self.player_y = ny
        self.player_cooldown = PLAYER_MOVE_DELAY

        # Check collision with ghosts after moving
        self._check_player_ghost_collision()

    def _collect_gem(self, gem: Gem) -> None:
        """Process gem collection: update combo, score, spawn replacement."""
        self.gems_eaten += 1
        if gem.color == -1:
            self.invincible_timer = INVINCIBLE_DURATION
            self.texts.append(
                FloatingText(
                    gem.x * CELL + CELL // 2,
                    gem.y * CELL,
                    "INVINC!",
                    pyxel.COLOR_WHITE,
                    60,
                )
            )
        elif gem.color == self.player_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            points = 10 * self.combo
            self.texts.append(
                FloatingText(
                    gem.x * CELL + CELL // 2,
                    gem.y * CELL,
                    f"x{self.combo}",
                    PX_COLORS[gem.color],
                    45,
                )
            )
            self.score += points
            self.player_color = gem.color
        else:
            self.combo = 1
            points = 10
            self.texts.append(
                FloatingText(
                    gem.x * CELL + CELL // 2,
                    gem.y * CELL,
                    "+10",
                    PX_COLORS[gem.color],
                    30,
                )
            )
            self.score += points
            self.player_color = gem.color

    def _check_player_ghost_collision(self) -> None:
        """Check if player occupies same cell as any ghost."""
        if self.invincible_timer > 0:
            for ghost in list(self.ghosts):
                if ghost.x == self.player_x and ghost.y == self.player_y:
                    self.ghosts.remove(ghost)
                    self.score += 50
                    self.texts.append(
                        FloatingText(
                            ghost.x * CELL + CELL // 2,
                            ghost.y * CELL,
                            "+50",
                            pyxel.COLOR_WHITE,
                            45,
                        )
                    )
        else:
            for ghost in self.ghosts:
                if ghost.x == self.player_x and ghost.y == self.player_y:
                    self.phase = Phase.GAME_OVER
                    return

    # ── Gems ──

    def _update_gems(self) -> None:
        """Check player-gem collisions and handle collection."""
        for gem in list(self.gems):
            if gem.x == self.player_x and gem.y == self.player_y:
                self.gems.remove(gem)
                self._collect_gem(gem)
                self._spawn_gem()
                break

    # ── Ghosts ──

    def _ghost_candidates(self, ghost: Ghost) -> list[tuple[int, int]]:
        """Return valid move candidates for a ghost, sorted by proximity to player."""
        candidates: list[tuple[int, int]] = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = ghost.x + dx, ghost.y + dy
            if self._is_blocked(nx, ny):
                continue
            if any(g is not ghost and g.x == nx and g.y == ny for g in self.ghosts):
                continue
            candidates.append((nx, ny))
        candidates.sort(
            key=lambda p: abs(p[0] - self.player_x) + abs(p[1] - self.player_y)
        )
        return candidates

    def _update_ghosts(self) -> None:
        """Move ghosts toward player; kill ghosts that step on dangerous trails."""
        self.ghost_cooldown -= 1
        if self.ghost_cooldown > 0:
            return
        self.ghost_cooldown = GHOST_MOVE_DELAY

        has_danger_trail = self.combo >= 2

        for ghost in list(self.ghosts):
            candidates = self._ghost_candidates(ghost)
            if not candidates:
                continue

            # If danger trails exist, prefer cells without trails
            if has_danger_trail and self.invincible_timer <= 0:
                safe = [c for c in candidates if not self._has_trail_at(c[0], c[1])]
                if safe:
                    candidates = safe

            nx, ny = candidates[0]

            # Ghost dies if stepping on danger trail
            if has_danger_trail and self.invincible_timer <= 0 and self._has_trail_at(nx, ny):
                self.ghosts.remove(ghost)
                bonus = 25 * self.combo
                self.score += bonus
                self.texts.append(
                    FloatingText(
                        nx * CELL + CELL // 2,
                        ny * CELL,
                        f"+{bonus}",
                        PX_COLORS[self.player_color],
                        45,
                    )
                )
                continue

            ghost.x, ghost.y = nx, ny

        # Check player collision after all ghosts have moved
        self._check_player_ghost_collision()

    # ── Effects ──

    def _update_trails(self) -> None:
        """Decay trail lifetimes; remove expired trails."""
        for trail in list(self.trails):
            trail.life -= 1
            if trail.life <= 0:
                self.trails.remove(trail)

    def _update_texts(self) -> None:
        """Float text upward and remove expired texts."""
        for text in list(self.texts):
            text.y -= 1
            text.life -= 1
            if text.life <= 0:
                self.texts.remove(text)

    # ── Spawning & Timers ──

    def _update_spawns(self) -> None:
        """Spawn new ghosts periodically (CA spread hook)."""
        self.ghost_spawn_timer -= 1
        if self.ghost_spawn_timer <= 0:
            self.ghost_spawn_timer = max(180, GHOST_SPAWN_INTERVAL - len(self.ghosts) * 30)
            self._spawn_ghost()

    def _update_timers(self) -> None:
        """Tick down invincibility timer."""
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    # ── Main Loop ──

    def update(self) -> None:
        """Per-frame update: handle input, game logic, and state transitions."""
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        self.frame += 1
        self._update_player()
        if self.phase == Phase.GAME_OVER:
            return
        self._update_gems()
        self._update_ghosts()
        self._update_trails()
        self._update_texts()
        self._update_spawns()
        self._update_timers()

    # ── Drawing ──

    def _draw_grid(self) -> None:
        """Clear screen, draw grid lines and obstacles."""
        pyxel.cls(pyxel.COLOR_BLACK)
        for x in range(0, SCREEN_W, CELL):
            pyxel.line(x, 0, x, SCREEN_H, pyxel.COLOR_NAVY)
        for y in range(0, SCREEN_H, CELL):
            pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_NAVY)
        for ox, oy in self._obstacles:
            pyxel.rect(
                ox * CELL + 1, oy * CELL + 1, CELL - 2, CELL - 2, pyxel.COLOR_GRAY
            )

    def _draw_trails(self) -> None:
        """Draw trail cells with fading intensity."""
        for trail in self.trails:
            alpha = trail.life / TRAIL_DURATION
            if alpha > 0.5:
                col = PX_DARK[trail.color]
            elif alpha > 0.2:
                col = pyxel.COLOR_NAVY
            else:
                continue
            pyxel.rect(
                trail.x * CELL + 2, trail.y * CELL + 2,
                CELL - 4, CELL - 4, col,
            )

    def _draw_gems(self) -> None:
        """Draw all gems (colored circles or flickering power gem)."""
        for gem in self.gems:
            cx = gem.x * CELL + CELL // 2
            cy = gem.y * CELL + CELL // 2
            r = CELL // 2 - 2
            if gem.color == -1:
                col = PX_COLORS[(self.frame // 4) % NUM_COLORS]
                pyxel.circ(cx, cy, r, col)
                pyxel.circ(cx, cy, r - 2, pyxel.COLOR_WHITE)
                pyxel.text(cx - 2, cy - 2, "P", pyxel.COLOR_BLACK)
            else:
                pyxel.circ(cx, cy, r, PX_COLORS[gem.color])
                pyxel.circ(cx - 1, cy - 1, r - 3, pyxel.COLOR_WHITE)

    def _draw_ghosts(self) -> None:
        """Draw all ghosts with animated wavy bottom."""
        for ghost in self.ghosts:
            gx = ghost.x * CELL + CELL // 2
            gy = ghost.y * CELL + CELL // 2
            r = CELL // 2 - 2

            if self.invincible_timer > 0:
                body_col = pyxel.COLOR_DARK_BLUE
            else:
                body_col = pyxel.COLOR_RED

            # Body
            pyxel.circ(gx, gy - 1, r, body_col)
            pyxel.rect(gx - r, gy - 1, r * 2, r + 1, body_col)
            # Wavy bottom
            wave = (self.frame // 5) % 2
            for i in range(3):
                sx = gx - r + 1 + i * 5
                sy = gy + r - wave
                pyxel.rect(sx, sy, 3, 2, body_col)
            # Eyes
            pyxel.circ(gx - 2, gy - 2, 2, pyxel.COLOR_WHITE)
            pyxel.circ(gx + 2, gy - 2, 2, pyxel.COLOR_WHITE)
            pyxel.circ(gx - 2, gy - 2, 1, pyxel.COLOR_BLACK)
            pyxel.circ(gx + 2, gy - 2, 1, pyxel.COLOR_BLACK)

    def _draw_player(self) -> None:
        """Draw the player character."""
        px = self.player_x * CELL + CELL // 2
        py = self.player_y * CELL + CELL // 2
        r = CELL // 2 - 1

        if self.invincible_timer > 0:
            if (self.frame // 3) % 2:
                col = pyxel.COLOR_WHITE
            else:
                col = PX_COLORS[(self.frame // 6) % NUM_COLORS]
            pyxel.circ(px, py, r + 1, col)
            pyxel.circ(px, py, r, pyxel.COLOR_BLACK)
            pyxel.circ(px, py, r - 2, col)
        elif self.player_color >= 0:
            col = PX_COLORS[self.player_color]
            pyxel.circ(px, py, r, col)
            pyxel.circ(px - 1, py - 1, r - 3, pyxel.COLOR_WHITE)
            pyxel.circ(px - 2, py - 2, 1, pyxel.COLOR_BLACK)
            pyxel.circ(px + 2, py - 2, 1, pyxel.COLOR_BLACK)
        else:
            pyxel.circ(px, py, r, pyxel.COLOR_WHITE)
            pyxel.circ(px - 2, py - 2, 1, pyxel.COLOR_BLACK)
            pyxel.circ(px + 2, py - 2, 1, pyxel.COLOR_BLACK)

    def _draw_texts(self) -> None:
        """Draw floating score/combo text effects."""
        for text in self.texts:
            pyxel.text(
                text.x - len(text.text) * 2,
                text.y,
                text.text,
                text.color,
            )

    def _draw_hud(self) -> None:
        """Draw score, combo, and status indicators."""
        pyxel.text(4, 2, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        if self.combo >= 2:
            combo_txt = f"COMBO x{self.combo}"
            px = SCREEN_W - len(combo_txt) * 4 - 4
            pyxel.text(px, 2, combo_txt, PX_COLORS[self.player_color])
        pyxel.text(4, 10, f"GEMS:{self.gems_eaten}", pyxel.COLOR_GRAY)
        pyxel.text(SCREEN_W - 56, 10, f"GHOSTS:{len(self.ghosts)}", pyxel.COLOR_RED)
        if self.invincible_timer > 0:
            secs = self.invincible_timer // FPS + 1
            pyxel.text(SCREEN_W // 2 - 20, 2, f"INV:{secs}s", pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        """Draw game over screen with stats and restart prompt."""
        pyxel.cls(pyxel.COLOR_BLACK)
        pyxel.text(
            SCREEN_W // 2 - 28, SCREEN_H // 2 - 20,
            "GAME OVER", pyxel.COLOR_RED,
        )
        pyxel.text(
            SCREEN_W // 2 - 48, SCREEN_H // 2 + 2,
            f"SCORE: {self.score}", pyxel.COLOR_WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 64, SCREEN_H // 2 + 14,
            f"GEMS: {self.gems_eaten}  MAX COMBO: {self.max_combo}",
            pyxel.COLOR_GRAY,
        )
        pyxel.text(
            SCREEN_W // 2 - 44, SCREEN_H // 2 + 34,
            "PRESS R TO RETRY", pyxel.COLOR_YELLOW,
        )

    def draw(self) -> None:
        """Per-frame draw: render all game elements or game-over screen."""
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return
        self._draw_grid()
        self._draw_trails()
        self._draw_gems()
        self._draw_ghosts()
        self._draw_player()
        self._draw_texts()
        self._draw_hud()


if __name__ == "__main__":
    Game()
