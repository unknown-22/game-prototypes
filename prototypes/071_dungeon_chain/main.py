"""071_dungeon_chain — Color-Match Roguelike Dungeon Crawler.

Core fun moment: killing same-color enemies consecutively to build COMBO chains,
then triggering ROOM SURGE to obliterate all same-color enemies in the room.
Risk/reward: committing to one color builds combo but switching costs HP.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
GRID_W = 16
GRID_H = 12
CELL = 20
SCREEN_W = GRID_W * CELL
SCREEN_H = GRID_H * CELL
ENEMY_MOVE_INTERVAL = 30
INVULN_FRAMES = 30

# Colors (raw ints)
BLACK = 0
NAVY = 1
PURPLE = 2
GREEN = 3
BROWN = 4
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
RED = 8
ORANGE = 9
YELLOW = 10
LIME = 11
CYAN = 12
GRAY = 13
PINK = 14
PEACH = 15

ENEMY_COLORS: tuple[int, int, int, int] = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "BLUE", "YELLOW")

# Tile types
TILE_WALL = 0
TILE_FLOOR = 1
TILE_DOOR = 2
TILE_KEY = 3
TILE_EXIT = 4

# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2
    VICTORY = 3


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Enemy:
    x: int
    y: int
    color: int
    hp: int = 1
    alive: bool = True


@dataclass
class Player:
    x: int
    y: int
    hp: int = 5
    max_hp: int = 5
    has_key: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Dungeon Chain", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self._init_state()

    def _init_state(self) -> None:
        self.score: int = 0
        self.combo: int = 0
        self.last_kill_color: int = -1
        self.max_combo: int = 0
        self.invuln_timer: int = 0
        self.enemy_move_timer: int = ENEMY_MOVE_INTERVAL
        self._frame: int = 0

        self.player = Player(x=1, y=1)
        self.enemies: list[Enemy] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self._build_dungeon()
        self._place_enemies()

    # ── Dungeon Building ────────────────────────────────────────────

    def _build_dungeon(self) -> None:
        self.dungeon: list[list[int]] = [[TILE_WALL] * GRID_W for _ in range(GRID_H)]

        # Room 1 (start): cols 1-8, rows 1-2
        for y in range(1, 3):
            for x in range(1, 9):
                self.dungeon[y][x] = TILE_FLOOR

        # Corridor down from room 1: cols 4-5, rows 3
        for x in range(4, 6):
            self.dungeon[3][x] = TILE_FLOOR

        # Room 2 (key room): cols 1-5, rows 4-6
        for y in range(4, 7):
            for x in range(1, 6):
                self.dungeon[y][x] = TILE_FLOOR

        # KEY in room 2
        self.dungeon[5][3] = TILE_KEY

        # Corridor right from room 2: cols 6-8, row 5
        for x in range(6, 9):
            self.dungeon[5][x] = TILE_FLOOR

        # Corridor down: col 7, rows 6-9
        for y in range(6, 10):
            self.dungeon[y][7] = TILE_FLOOR

        # Room 3 (main room): cols 1-9, rows 8-10
        for y in range(8, 11):
            for x in range(1, 10):
                if self.dungeon[y][x] == TILE_WALL:
                    self.dungeon[y][x] = TILE_FLOOR

        # Corridor from room 3 going right and up: col 10, rows 5-10
        for y in range(5, 11):
            self.dungeon[y][10] = TILE_FLOOR

        # DOOR at (10, 4) blocks path to exit area
        self.dungeon[4][10] = TILE_DOOR

        # Corridor above door: col 10, rows 2-3
        for y in range(2, 4):
            self.dungeon[y][10] = TILE_FLOOR

        # Exit room: cols 10-14, rows 1-2
        for y in range(1, 3):
            for x in range(10, 15):
                if self.dungeon[y][x] in (TILE_WALL, TILE_FLOOR):
                    self.dungeon[y][x] = TILE_FLOOR
                elif x == 10 and y < 4:
                    continue

        # Overwrite with floor for the exit room, but exit tile stays
        for y in range(1, 3):
            for x in range(11, 15):
                self.dungeon[y][x] = TILE_FLOOR

        # EXIT tile
        self.dungeon[1][14] = TILE_EXIT

        # Corridor connecting room 1 bottom-right to room 2 top: col 8, row 3
        self.dungeon[3][8] = TILE_FLOOR

    def _place_enemies(self) -> None:
        self.enemies.clear()
        # Room 1: 1 enemy
        self.enemies.append(Enemy(x=3, y=1, color=RED))
        # Room 2: 2 enemies
        self.enemies.append(Enemy(x=2, y=4, color=GREEN))
        self.enemies.append(Enemy(x=4, y=6, color=GREEN))
        # Room 3: 3 enemies
        self.enemies.append(Enemy(x=3, y=9, color=RED))
        self.enemies.append(Enemy(x=6, y=8, color=DARK_BLUE))
        self.enemies.append(Enemy(x=8, y=10, color=DARK_BLUE))
        # Exit room: 1 enemy
        self.enemies.append(Enemy(x=12, y=1, color=YELLOW))

    # ── Pure Logic: Room Detection ──────────────────────────────────

    def _get_room_cells(self, sx: int, sy: int) -> set[tuple[int, int]]:
        """BFS flood-fill on FLOOR tiles. Returns set of (x,y) in same room."""
        if not (0 <= sx < GRID_W and 0 <= sy < GRID_H):
            return set()
        if self.dungeon[sy][sx] == TILE_WALL:
            return set()
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(sx, sy)]
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        while queue:
            x, y = queue.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                    if (nx, ny) not in visited and self.dungeon[ny][nx] in (TILE_FLOOR, TILE_KEY):
                        queue.append((nx, ny))
        return visited

    # ── Pure Logic: Combat ──────────────────────────────────────────

    def _find_adjacent_enemy(self, px: int, py: int) -> Enemy | None:
        """Return the first adjacent alive enemy (Manhattan distance 1)."""
        for e in self.enemies:
            if e.alive and abs(e.x - px) + abs(e.y - py) == 1:
                return e
        return None

    def _attack_enemy(self, enemy: Enemy) -> None:
        """Pure logic: attack an enemy, handle combo, damage, score."""
        if not enemy.alive:
            return

        enemy.alive = False
        self._spawn_particles(enemy.x, enemy.y, enemy.color)

        if self.combo == 0 or enemy.color == self.last_kill_color:
            self.combo += 1
            self.last_kill_color = enemy.color
        else:
            self.player.hp -= 1
            self.combo = 1
            self.last_kill_color = enemy.color

        points = 100 * self.combo
        self.score += points
        self.max_combo = max(self.max_combo, self.combo)
        self._spawn_floating_text(enemy.x, enemy.y, f"+{points}", enemy.color)

        if self.combo >= 4:
            self._bfs_surge(enemy.x, enemy.y, enemy.color)

    def _bfs_surge(self, start_x: int, start_y: int, color: int) -> None:
        """BFS chain-kill same-color enemies in the same room."""
        room_cells = self._get_room_cells(start_x, start_y)
        if not room_cells:
            return

        queue: list[tuple[int, int]] = [(start_x, start_y)]
        visited: set[tuple[int, int]] = set()
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        killed = 0

        while queue:
            cx, cy = queue.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in visited:
                    continue
                if (nx, ny) not in room_cells:
                    continue
                for e in self.enemies:
                    if e.x == nx and e.y == ny and e.alive and e.color == color:
                        e.alive = False
                        killed += 1
                        self.combo += 1
                        self._spawn_particles(nx, ny, color)
                        queue.append((nx, ny))
                        break

        if killed > 0:
            self.score += killed * 50 * self.combo
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_floating_text(
                GRID_W // 2, GRID_H // 2,
                "ROOM SURGE!", color, life=40,
            )

    # ── Pure Logic: Movement ────────────────────────────────────────

    def _move_player(self, dx: int, dy: int) -> None:
        """Move player if target tile is passable. Collect key / unlock door."""
        nx = self.player.x + dx
        ny = self.player.y + dy
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
            return

        tile = self.dungeon[ny][nx]
        if tile == TILE_WALL:
            return
        if tile == TILE_DOOR and not self.player.has_key:
            return

        if tile == TILE_KEY:
            self.player.has_key = True
            self.dungeon[ny][nx] = TILE_FLOOR

        if tile == TILE_DOOR and self.player.has_key:
            self.dungeon[ny][nx] = TILE_FLOOR

        self.player.x = nx
        self.player.y = ny

    # ── Pure Logic: Enemy AI ────────────────────────────────────────

    def _update_enemies(self) -> None:
        """Move enemies toward player, apply contact damage."""
        if self.enemy_move_timer > 0:
            self.enemy_move_timer -= 1
            return
        self.enemy_move_timer = ENEMY_MOVE_INTERVAL

        px, py = self.player.x, self.player.y

        for e in self.enemies:
            if not e.alive:
                continue

            dist = abs(e.x - px) + abs(e.y - py)
            if dist > 6:
                continue

            dx = 0
            dy = 0
            if e.x < px:
                dx = 1
            elif e.x > px:
                dx = -1

            if e.y < py:
                dy = 1
            elif e.y > py:
                dy = -1

            if dx != 0 and dy != 0:
                if self._rng.random() < 0.5:
                    dy = 0
                else:
                    dx = 0

            if dx != 0 or dy != 0:
                nx = e.x + dx
                ny = e.y + dy
                tile = self.dungeon[ny][nx]
                if tile in (TILE_FLOOR,):
                    blocked = any(
                        e2.alive and e2.x == nx and e2.y == ny
                        for e2 in self.enemies if e2 is not e
                    )
                    if not blocked:
                        e.x = nx
                        e.y = ny

            if e.x == px and e.y == py:
                if self.invuln_timer <= 0:
                    self.player.hp -= 1
                    self.invuln_timer = INVULN_FRAMES
                    self._spawn_particles(px, py, RED, count=4)

    # ── Particles and Floating Text ─────────────────────────────────

    def _spawn_particles(self, gx: int, gy: int, color: int, count: int = 6) -> None:
        """Spawn kill particles at grid position."""
        cx = gx * CELL + CELL / 2
        cy = gy * CELL + CELL / 2
        for _ in range(count):
            self.particles.append(Particle(
                x=cx,
                y=cy,
                vx=self._rng.uniform(-1.2, 1.2),
                vy=self._rng.uniform(-1.2, 1.2),
                life=15 + self._rng.randint(0, 5),
                color=color,
            ))

    def _spawn_floating_text(self, gx: int | float, gy: int | float, text: str, color: int, life: int = 20) -> None:
        """Spawn floating text at grid or pixel position."""
        if isinstance(gx, int) and isinstance(gy, int):
            cx = gx * CELL + CELL / 2
            cy = gy * CELL
        else:
            cx = gx
            cy = gy
        self.floating_texts.append(FloatingText(
            x=float(cx), y=float(cy), text=text, life=life, color=color,
        ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ── Click Handling ──────────────────────────────────────────────

    def _handle_attack_nearest(self) -> None:
        """Attack nearest adjacent enemy via keyboard."""
        enemy = self._find_adjacent_enemy(self.player.x, self.player.y)
        if enemy is not None:
            self._attack_enemy(enemy)

    def _handle_click(self, mouse_px: int, mouse_py: int) -> None:
        """Convert pixel coords, find adjacent enemy, attack."""
        gx = mouse_px // CELL
        gy = mouse_py // CELL
        px, py = self.player.x, self.player.y
        for e in self.enemies:
            if not e.alive:
                continue
            if abs(e.x - px) + abs(e.y - py) != 1:
                continue
            if abs(e.x - gx) + abs(e.y - gy) <= 1:
                self._attack_enemy(e)
                return

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        self._frame += 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase in (Phase.GAME_OVER, Phase.VICTORY):
            self._update_end_screen()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self._init_state()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._update_enemies()
        self._update_particles()
        self._update_floating_texts()

        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        # Movement
        if pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_UP):
            self._move_player(0, -1)
        elif pyxel.btnp(pyxel.KEY_S) or pyxel.btnp(pyxel.KEY_DOWN):
            self._move_player(0, 1)
        elif pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_LEFT):
            self._move_player(-1, 0)
        elif pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_RIGHT):
            self._move_player(1, 0)

        # Attack
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._handle_attack_nearest()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

        # Check victory
        if self.dungeon[self.player.y][self.player.x] == TILE_EXIT:
            self.phase = Phase.VICTORY

        # Check game over
        if self.player.hp <= 0:
            self.phase = Phase.GAME_OVER

    def _update_end_screen(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._init_state()
            self.phase = Phase.PLAYING

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.VICTORY:
            self._draw_victory()

    def _draw_title(self) -> None:
        title = "DUNGEON CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 50, title, WHITE)

        lines = [
            "WASD: Move",
            "SPACE: Attack nearest enemy",
            "Mouse Click: Attack enemy under cursor",
            "",
            "Kill same-color enemies for COMBO!",
            "COMBO x4 = ROOM SURGE!",
            "Wrong color = HP loss + COMBO reset",
            "",
            "ENTER or SPACE to Start",
        ]
        for i, line in enumerate(lines):
            if line:
                pyxel.text(SCREEN_W // 2 - len(line) * 4 // 2, 80 + i * 12, line, GRAY)

    def _draw_playing(self) -> None:
        self._draw_dungeon()
        self._draw_enemies()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_dungeon(self) -> None:
        for y in range(GRID_H):
            for x in range(GRID_W):
                tile = self.dungeon[y][x]
                px = x * CELL
                py = y * CELL
                if tile == TILE_WALL:
                    pyxel.rect(px, py, CELL, CELL, GRAY)
                    pyxel.rectb(px, py, CELL, CELL, DARK_BLUE)
                elif tile == TILE_FLOOR:
                    pyxel.rect(px, py, CELL, CELL, NAVY)
                    pyxel.rectb(px, py, CELL, CELL, LIGHT_BLUE)
                elif tile == TILE_DOOR:
                    pyxel.rect(px, py, CELL, CELL, ORANGE)
                    pyxel.rectb(px, py, CELL, CELL, YELLOW)
                elif tile == TILE_KEY:
                    pyxel.rect(px, py, CELL, CELL, NAVY)
                    pyxel.rectb(px, py, CELL, CELL, LIGHT_BLUE)
                    cx = px + CELL // 2
                    cy = py + CELL // 2
                    pyxel.circ(cx, cy, 4, YELLOW)
                elif tile == TILE_EXIT:
                    pyxel.rect(px, py, CELL, CELL, NAVY)
                    pyxel.rectb(px, py, CELL, CELL, LIME)

    def _draw_player(self) -> None:
        px = self.player.x * CELL
        py = self.player.y * CELL
        if self.invuln_timer > 0 and (self._frame // 4) % 2 == 0:
            return
        pyxel.rect(px + 2, py + 2, CELL - 4, CELL - 4, WHITE)
        pyxel.rectb(px + 2, py + 2, CELL - 4, CELL - 4, LIGHT_BLUE)

    def _draw_enemies(self) -> None:
        for e in self.enemies:
            if not e.alive:
                continue
            px = e.x * CELL
            py = e.y * CELL
            size = CELL - 6
            ox = (CELL - size) // 2
            oy = (CELL - size) // 2
            pyxel.rect(px + ox, py + oy, size, size, e.color)
            pyxel.rectb(px + ox, py + oy, size, size, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, SCREEN_H - 16, SCREEN_W, 16, NAVY)
        pyxel.line(0, SCREEN_H - 16, SCREEN_W, SCREEN_H - 16, WHITE)

        hp_str = "HP:" + "|" * self.player.hp
        pyxel.text(4, SCREEN_H - 14, hp_str, RED)

        key_status = "KEY:Y" if self.player.has_key else "KEY:N"
        c = YELLOW if self.player.has_key else GRAY
        pyxel.text(4 + 60, SCREEN_H - 14, key_status, c)

        combo_str = f"COMBO:x{self.combo}"
        combo_c = YELLOW if self.combo >= 4 else WHITE
        pyxel.text(SCREEN_W // 2 - len(combo_str) * 4 // 2, SCREEN_H - 14, combo_str, combo_c)

        score_str = f"SCORE:{self.score}"
        pyxel.text(SCREEN_W - len(score_str) * 4 - 4, SCREEN_H - 14, score_str, WHITE)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, NAVY)
        pyxel.rectb(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, RED)

        msg = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(msg) * 4 // 2, SCREEN_H // 2 - 40, msg, RED)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 - 20, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, SCREEN_H // 2 - 5, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 20, "R to Retry", WHITE)

    def _draw_victory(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, NAVY)
        pyxel.rectb(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, LIME)

        msg = "DUNGEON CLEAR!"
        pyxel.text(SCREEN_W // 2 - len(msg) * 4 // 2, SCREEN_H // 2 - 40, msg, LIME)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 - 20, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, SCREEN_H // 2 - 5, f"MAX COMBO: {self.max_combo}", YELLOW)
        hp_text = f"HP REMAINING: {self.player.hp}"
        pyxel.text(SCREEN_W // 2 - len(hp_text) * 4 // 2, SCREEN_H // 2 + 10, hp_text, GREEN)
        pyxel.text(SCREEN_W // 2 - 45, SCREEN_H // 2 + 25, "R to Play Again", WHITE)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
