"""ECHO HOP — Isometric Color-Chain Hopping (Q*bert-style)"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30

BLACK = 0
NAVY = 1
DARK_BLUE = 5
WHITE = 7
RED = 8
YELLOW = 10
LIME = 11
GRAY = 13

COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "DARK_BLUE", "YELLOW")

GRID_SIZE = 7
CUBE_W = 24
CUBE_H = 12
ORIGIN_X = SCREEN_W // 2
ORIGIN_Y = 40

MAX_FOOTPRINTS = 5
FOOTPRINT_LIFE = 180

MOVE_COOLDOWN = 8
ENEMY_MOVE_INTERVAL = 45

SUPER_THRESHOLD = 4
SUPER_DURATION = 300

SPAWN_INTERVAL_START = 120
SPAWN_INTERVAL_MIN = 40
DIFFICULTY_RAMP_FRAMES = 3600

MAX_HP = 5

BFS_BONUS = 50
KILL_BASE_SCORE = 10
FALL_PENALTY = -5


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class Enemy:
    grid_x: int
    grid_y: int
    color: int
    alive: bool = True


@dataclass
class Footprint:
    grid_x: int
    grid_y: int
    color: int
    life: int


class Game:
    """Isometric color-chain hopping game."""

    def __new__(cls, headless: bool = False) -> Game:
        obj = object.__new__(cls)
        obj._set_defaults()
        obj._headless = headless
        return obj

    def _set_defaults(self) -> None:
        self._headless: bool = False
        self.phase: Phase = Phase.TITLE
        self.player_gx: int = 0
        self.player_gy: int = 0
        self.active_color: int = RED
        self.combo: int = 0
        self.max_combo: int = 0
        self.hp: int = MAX_HP
        self.score: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.enemies: list[Enemy] = []
        self.footprints: list[Footprint] = []
        self.particles: list[Particle] = []
        self.spawn_timer: int = 30
        self.spawn_interval: int = SPAWN_INTERVAL_START
        self.game_timer: int = 0
        self.move_cooldown: int = 0
        self.enemy_move_timer: int = 0
        self._rng: random.Random = random.Random()

    def __init__(self, headless: bool = False) -> None:
        if headless:
            return
        pyxel.init(SCREEN_W, SCREEN_H, title="Echo Hop", fps=FPS)
        self.reset()
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_gx = 0
        self.player_gy = 0
        self.active_color = COLORS[self._rng.randint(0, 3)]
        self.combo = 0
        self.max_combo = 0
        self.hp = MAX_HP
        self.score = 0
        self.super_mode = False
        self.super_timer = 0
        self.enemies.clear()
        self.footprints.clear()
        self.particles.clear()
        self.spawn_timer = 30
        self.spawn_interval = SPAWN_INTERVAL_START
        self.game_timer = 0
        self.move_cooldown = 0
        self.enemy_move_timer = 0

    def reset_for_playing(self) -> None:
        self.player_gx = 0
        self.player_gy = 0
        self.active_color = COLORS[self._rng.randint(0, 3)]
        self.combo = 0
        self.max_combo = 0
        self.hp = MAX_HP
        self.score = 0
        self.super_mode = False
        self.super_timer = 0
        self.enemies.clear()
        self.footprints.clear()
        self.particles.clear()
        self.spawn_timer = 30
        self.spawn_interval = SPAWN_INTERVAL_START
        self.game_timer = 0
        self.move_cooldown = 0
        self.enemy_move_timer = 0

    # ── Input ────────────────────────────────────────────────────────────

    def _get_input(self) -> dict:
        if self._headless:
            return {
                "up": False,
                "right": False,
                "down": False,
                "left": False,
                "space_p": False,
                "return_p": False,
            }
        return {
            "up": pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W),
            "right": pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D),
            "down": pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S),
            "left": pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A),
            "space_p": pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN),
            "return_p": pyxel.btnp(pyxel.KEY_RETURN),
        }

    # ── Isometric Projection ──────────────────────────────────────────────

    def _grid_to_screen(self, gx: int, gy: int) -> tuple[float, float]:
        sx = ORIGIN_X + (gx - gy) * (CUBE_W // 2)
        sy = ORIGIN_Y + (gx + gy) * (CUBE_H // 2)
        return (sx, sy)

    def _is_valid_cube(self, gx: int, gy: int) -> bool:
        if not (0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE):
            return False
        return gx + gy < GRID_SIZE

    def _get_neighbors(self, gx: int, gy: int) -> list[tuple[int, int]]:
        dirs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        result: list[tuple[int, int]] = []
        for dx, dy in dirs:
            nx, ny = gx + dx, gy + dy
            if self._is_valid_cube(nx, ny):
                result.append((nx, ny))
        return result

    # ── Enemy Helpers ─────────────────────────────────────────────────────

    def _enemy_at(self, gx: int, gy: int) -> list[Enemy]:
        return [e for e in self.enemies if e.grid_x == gx and e.grid_y == gy and e.alive]

    # ── Player Movement ──────────────────────────────────────────────────

    def _move_player(self, dx: int, dy: int) -> bool:
        gx = self.player_gx + dx
        gy = self.player_gy + dy

        if not self._is_valid_cube(gx, gy):
            self.hp -= 1
            self.score = max(0, self.score + FALL_PENALTY)
            self.player_gx = 0
            self.player_gy = 0
            self.combo = 0
            self.active_color = COLORS[self._rng.randint(0, 3)]
            return True

        enemies_here = self._enemy_at(gx, gy)
        if enemies_here:
            for enemy in enemies_here:
                if enemy.color == self.active_color:
                    self._stomp_enemy(enemy)
                else:
                    self.hp -= 1
                    self.combo = 0

        self._leave_footprint(gx, gy)
        self.player_gx = gx
        self.player_gy = gy
        return True

    def _leave_footprint(self, gx: int, gy: int) -> None:
        new_color = self.active_color
        while new_color == self.active_color:
            new_color = COLORS[self._rng.randint(0, 3)]
        self.footprints = [f for f in self.footprints if not (f.grid_x == gx and f.grid_y == gy)]
        self.footprints.append(Footprint(gx, gy, new_color, FOOTPRINT_LIFE))
        if len(self.footprints) > MAX_FOOTPRINTS:
            self.footprints.sort(key=lambda f: f.life)
            self.footprints.pop(0)
        self.active_color = new_color

    def _stomp_enemy(self, enemy: Enemy) -> bool:
        enemy.alive = False
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        multiplier = 3 if self.super_mode else 1
        self.score += int(KILL_BASE_SCORE * self.combo * multiplier)
        self._spawn_particles(enemy.grid_x, enemy.grid_y, enemy.color, 5, 10)

        self._check_super_mode()

        if self.super_mode:
            chain = self._bfs_clear(enemy.grid_x, enemy.grid_y, enemy.color)
            for cgx, cgy in chain:
                for e in self._enemy_at(cgx, cgy):
                    if e.alive:
                        e.alive = False
                        self.score += BFS_BONUS
                        self._spawn_particles(cgx, cgy, e.color, 15, 30)

        return True

    def _check_super_mode(self) -> None:
        if self.combo >= SUPER_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION

    def _bfs_clear(self, gx: int, gy: int, color: int) -> list[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        result: list[tuple[int, int]] = []
        queue: deque[tuple[int, int]] = deque()
        visited.add((gx, gy))
        queue.append((gx, gy))

        while queue:
            cx, cy = queue.popleft()
            enemies_here = self._enemy_at(cx, cy)
            if any(e.alive and e.color == color for e in enemies_here):
                result.append((cx, cy))
            for nx, ny in self._get_neighbors(cx, cy):
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    if any(e.grid_x == nx and e.grid_y == ny and e.alive and e.color == color
                           for e in self.enemies):
                        queue.append((nx, ny))
        return result

    # ── Enemy Spawn ───────────────────────────────────────────────────────

    def _get_edge_cubes(self) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                if not self._is_valid_cube(gx, gy):
                    continue
                neighbors = self._get_neighbors(gx, gy)
                if len(neighbors) < 4:
                    result.append((gx, gy))
        return result

    def _spawn_enemy(self) -> Enemy | None:
        edges = self._get_edge_cubes()
        candidates = [(gx, gy) for gx, gy in edges
                      if not self._enemy_at(gx, gy)
                      and (gx, gy) != (self.player_gx, self.player_gy)]
        if not candidates:
            return None
        gx, gy = self._rng.choice(candidates)
        color = COLORS[self._rng.randint(0, 3)]
        enemy = Enemy(gx, gy, color)
        self.enemies.append(enemy)
        return enemy

    # ── Enemy Update ──────────────────────────────────────────────────────

    def _update_enemies(self) -> None:
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            gx, gy = enemy.grid_x, enemy.grid_y
            neighbors = self._get_neighbors(gx, gy)
            if not neighbors:
                continue
            current_dist = abs(gx - self.player_gx) + abs(gy - self.player_gy)
            best = (gx, gy)
            best_dist = current_dist
            for nx, ny in neighbors:
                nd = abs(nx - self.player_gx) + abs(ny - self.player_gy)
                if nd < best_dist and not self._enemy_at(nx, ny) and (
                        nx, ny) != (self.player_gx, self.player_gy):
                    best_dist = nd
                    best = (nx, ny)
            enemy.grid_x, enemy.grid_y = best

    # ── Update Systems ────────────────────────────────────────────────────

    def _update_footprints(self) -> None:
        for fp in self.footprints:
            fp.life -= 1
        self.footprints = [f for f in self.footprints if f.life > 0]

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_spawn_timer(self) -> None:
        if self.game_timer < DIFFICULTY_RAMP_FRAMES:
            ratio = self.game_timer / DIFFICULTY_RAMP_FRAMES
            self.spawn_interval = SPAWN_INTERVAL_START - int(
                (SPAWN_INTERVAL_START - SPAWN_INTERVAL_MIN) * ratio
            )
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            if len([e for e in self.enemies if e.alive]) < 12:
                self._spawn_enemy()
            self.spawn_timer = self.spawn_interval

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _cleanup_dead_enemies(self) -> None:
        self.enemies = [e for e in self.enemies if e.alive]

    # ── Particles ─────────────────────────────────────────────────────────

    def _spawn_particles(self, gx: int, gy: int, color: int, min_count: int, max_count: int) -> None:
        sx, sy = self._grid_to_screen(gx, gy)
        count = self._rng.randint(min_count, max_count)
        for _ in range(count):
            angle = self._rng.uniform(0, 6.283185)
            speed = self._rng.uniform(1.0, 3.5)
            vx = speed * (1 if angle < 3.1416 else -1) * abs(self._rng.uniform(0.3, 1.0))
            vy = -self._rng.uniform(1.0, 3.0)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(sx, sy, vx, vy, life, color))

    # ── Update ────────────────────────────────────────────────────────────

    def _update(self) -> None:
        inp = self._get_input()

        if self.phase == Phase.TITLE:
            self._update_title(inp)
        elif self.phase == Phase.PLAYING:
            self._update_playing(inp)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(inp)

    def _update_title(self, inp: dict) -> None:
        if inp["space_p"] or inp["return_p"]:
            self.reset_for_playing()
            self.phase = Phase.PLAYING

    def _update_playing(self, inp: dict) -> None:
        if self.hp <= 0:
            self.phase = Phase.GAME_OVER
            return

        self.game_timer += 1

        if self.move_cooldown > 0:
            self.move_cooldown -= 1

        if self.move_cooldown == 0:
            moved = False
            if inp["up"]:
                moved = self._move_player(-1, -1)
            elif inp["right"]:
                moved = self._move_player(1, -1)
            elif inp["down"]:
                moved = self._move_player(1, 1)
            elif inp["left"]:
                moved = self._move_player(-1, 1)
            if moved:
                self.move_cooldown = MOVE_COOLDOWN

        self._update_super()
        self._update_spawn_timer()
        self.enemy_move_timer += 1
        if self.enemy_move_timer >= ENEMY_MOVE_INTERVAL:
            self.enemy_move_timer = 0
            self._update_enemies()
        self._update_footprints()
        self._update_particles()
        self._cleanup_dead_enemies()

    def _update_game_over(self, inp: dict) -> None:
        if inp["space_p"] or inp["return_p"]:
            self.reset_for_playing()
            self.phase = Phase.PLAYING

    # ── Drawing ───────────────────────────────────────────────────────────

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_cubes(self) -> None:
        all_cubes: list[tuple[int, int]] = []
        for gx in range(GRID_SIZE):
            for gy in range(GRID_SIZE):
                if self._is_valid_cube(gx, gy):
                    all_cubes.append((gx, gy))
        all_cubes.sort(key=lambda c: c[0] + c[1])

        for gx, gy in all_cubes:
            cx, cy = self._grid_to_screen(gx, gy)
            color = DARK_BLUE if (gx + gy) % 2 == 0 else NAVY
            hw = CUBE_W // 2
            hh = CUBE_H // 2
            pyxel.tri(cx, cy - hh, cx + hw, cy, cx, cy + hh, color)
            pyxel.tri(cx, cy - hh, cx - hw, cy, cx, cy + hh, color)

    def _draw_footprints(self) -> None:
        for fp in self.footprints:
            cx, cy = self._grid_to_screen(fp.grid_x, fp.grid_y)
            alpha = max(1, fp.life / FOOTPRINT_LIFE)
            size = int(3 * alpha)
            if size > 0:
                pyxel.circ(int(cx), int(cy), size, fp.color)

    def _draw_enemies(self) -> None:
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            cx, cy = self._grid_to_screen(enemy.grid_x, enemy.grid_y)
            size = 4
            if self.super_mode:
                color = COLORS[self.game_timer // 8 % 4]
            else:
                color = enemy.color
            pyxel.rect(int(cx) - size, int(cy) - size, size * 2, size * 2, color)
            pyxel.rectb(int(cx) - size, int(cy) - size, size * 2, size * 2, BLACK)

    def _draw_player(self) -> None:
        cx, cy = self._grid_to_screen(self.player_gx, self.player_gy)
        if self.super_mode:
            color = COLORS[self.game_timer // 4 % 4]
        else:
            color = self.active_color
        pyxel.circ(int(cx), int(cy), 5, color)
        pyxel.circb(int(cx), int(cy), 5, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25
            size = max(1, int(3 * alpha))
            if size > 0:
                pyxel.circ(int(p.x), int(p.y), size, p.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)
        pyxel.text(4, 12, f"COMBO:{self.combo}", WHITE)
        hp_text = "".join("O" if i < self.hp else "." for i in range(MAX_HP))
        pyxel.text(4, 20, f"HP:{hp_text}", WHITE)
        pyxel.text(4, 28, f"COLOR:{COLOR_NAMES[COLORS.index(self.active_color)]}", self.active_color)
        if self.super_mode:
            bar_w = 80
            ratio = self.super_timer / SUPER_DURATION
            pyxel.rect(SCREEN_W // 2 - bar_w // 2, SCREEN_H - 16, bar_w, 6, GRAY)
            pyxel.rect(SCREEN_W // 2 - bar_w // 2, SCREEN_H - 16, int(bar_w * ratio), 6, YELLOW)
            pyxel.text(SCREEN_W // 2 - 20, SCREEN_H - 28, "SUPER!", YELLOW)
        self._cleanup_dead_enemies()
        enemy_count = len([e for e in self.enemies if e.alive])
        pyxel.text(SCREEN_W - 60, 4, f"ENEMIES:{enemy_count}", WHITE)

    def _draw_playing(self) -> None:
        self._draw_cubes()
        self._draw_footprints()
        self._draw_enemies()
        self._draw_player()
        self._draw_particles()
        self._draw_hud()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 40, "ECHO HOP", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2, "Press SPACE to start", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, SCREEN_H // 2 + 20, "Arrow/WASD: Move", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, SCREEN_H // 2 + 30, "Stomp same-color enemies", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, SCREEN_H // 2 + 40, "Build COMBO for SUPER HOP", GRAY)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 55, "Colors: RED LIME BLUE YELLOW", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 30, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 12, f"MAX COMBO: {self.max_combo}", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 + 30, "Press SPACE to retry", GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
