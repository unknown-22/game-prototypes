import pyxel
import random
from dataclasses import dataclass

COLS = 20
ROWS = 14
CELL = 16
NUM_COLORS = 4
DIRT_COLORS = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
MAX_LIVES = 3
ENEMY_MOVE_INTERVAL_BASE = 18
ROCK_FALL_FRAMES = 18  # ~0.3s at 60fps
INVULN_FRAMES = 90
LEVEL_CLEAR_FRAMES = 60


@dataclass
class Enemy:
    x: int
    y: int
    move_timer: int = 0


@dataclass
class Rock:
    x: int
    y: int
    fall_timer: int = 0
    falling: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.grid: list[list[int]] = [[-1 for _ in range(COLS)] for _ in range(ROWS)]
        self.player_x: int = COLS // 2
        self.player_y: int = 1
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_dug_color: int | None = None
        self.score: int = 0
        self.lives: int = MAX_LIVES
        self.level: int = 1
        self.enemies: list[Enemy] = []
        self.rocks: list[Rock] = []
        self.particles: list[Particle] = []
        self.phase: str = "title"
        self.invuln_timer: int = 0
        self.level_clear_timer: int = 0
        self._generate_level()

    def _generate_level(self) -> None:
        for y in range(2, ROWS):
            for x in range(COLS):
                self.grid[y][x] = self._rng.randint(0, NUM_COLORS - 1)
        self.player_x = COLS // 2
        self.player_y = 1
        self.combo = 0
        self.last_dug_color = None
        self._spawn_enemies()
        self._spawn_rocks()

    def _spawn_enemies(self) -> None:
        self.enemies.clear()
        count = 2 + (self.level - 1)
        empty_cells: list[tuple[int, int]] = []
        for y in range(2):
            for x in range(COLS):
                empty_cells.append((x, y))
        self._rng.shuffle(empty_cells)
        for i in range(min(count, len(empty_cells))):
            x, y = empty_cells[i]
            self.enemies.append(Enemy(x=x, y=y))

    def _spawn_rocks(self) -> None:
        self.rocks.clear()
        count = self._rng.randint(5, 8)
        dirt_cells: list[tuple[int, int]] = []
        for y in range(2, ROWS):
            for x in range(COLS):
                if self._is_dirt(x, y):
                    dirt_cells.append((x, y))
        self._rng.shuffle(dirt_cells)
        placed = 0
        for x, y in dirt_cells:
            if placed >= count:
                break
            if any(r.x == x and r.y == y for r in self.rocks):
                continue
            self.rocks.append(Rock(x=x, y=y))
            placed += 1

    def _is_dirt(self, cx: int, cy: int) -> bool:
        if not (0 <= cx < COLS and 0 <= cy < ROWS):
            return False
        return self.grid[cy][cx] >= 0

    def _is_empty(self, cx: int, cy: int) -> bool:
        if not (0 <= cx < COLS and 0 <= cy < ROWS):
            return False
        return self.grid[cy][cx] == -1

    def _is_rock(self, cx: int, cy: int) -> bool:
        return any(r.x == cx and r.y == cy for r in self.rocks)

    def _is_enemy(self, cx: int, cy: int) -> bool:
        return any(e.x == cx and e.y == cy for e in self.enemies)

    def _check_converge(self, cx: int, cy: int) -> bool:
        empty_neighbors: list[tuple[int, int]] = []
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if self._is_empty(nx, ny):
                empty_neighbors.append((nx, ny))
        if len(empty_neighbors) < 2:
            return False
        region = self._bfs_empty(empty_neighbors[0][0], empty_neighbors[0][1])
        for i in range(1, len(empty_neighbors)):
            if empty_neighbors[i] not in region:
                return True
        return False

    def _bfs_empty(self, sx: int, sy: int) -> set[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(sx, sy)]
        visited.add((sx, sy))
        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and self._is_empty(nx, ny):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return visited

    def _bfs_same_color_dirt(self, sx: int, sy: int, color: int) -> set[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(sx, sy)]
        visited.add((sx, sy))
        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and 0 <= nx < COLS and 0 <= ny < ROWS:
                    if self.grid[ny][nx] == color:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return visited

    def _dig(self, cx: int, cy: int) -> None:
        color = self.grid[cy][cx]
        if color < 0:
            return
        is_converge = self._check_converge(cx, cy)
        if self.last_dug_color is not None and color == self.last_dug_color:
            self.combo += 1
        else:
            self.combo = 1
        self.last_dug_color = color
        self.max_combo = max(self.max_combo, self.combo)
        self.grid[cy][cx] = -1
        score_gain = 10 * self.combo
        self.score += score_gain
        self._spawn_particles(cx, cy, DIRT_COLORS[color], 3)
        if is_converge:
            chain_cells = self._bfs_same_color_dirt(cx, cy, color)
            if len(chain_cells) > 0:
                chain_score = len(chain_cells) * 50 * self.combo
                self.score += chain_score
                killed_positions: set[tuple[int, int]] = set()
                for dx, dy in chain_cells:
                    self.grid[dy][dx] = -1
                    self._spawn_particles(dx, dy, DIRT_COLORS[color], 2)
                    for ndx, ndy in ((dx - 1, dy), (dx + 1, dy), (dx, dy - 1), (dx, dy + 1)):
                        killed_positions.add((ndx, ndy))
                for enemy in self.enemies[:]:
                    if (enemy.x, enemy.y) in killed_positions:
                        self.enemies.remove(enemy)
                        self.score += 200
                        self._spawn_particles(enemy.x, enemy.y, pyxel.COLOR_ORANGE, 8)

    def _collapse_chain(self, cells: set[tuple[int, int]]) -> int:
        score = 0
        for dx, dy in cells:
            if self._is_dirt(dx, dy):
                self.grid[dy][dx] = -1
                score += 50
                self._spawn_particles(dx, dy, pyxel.COLOR_CYAN, 3)
        return score * self.combo

    def _spawn_particles(self, cx: int, cy: int, color: int, count: int = 5) -> None:
        px = cx * CELL + CELL // 2
        py = cy * CELL + CELL // 2
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-2.5, -0.5)
            life = self._rng.randint(8, 22)
            self.particles.append(Particle(
                x=px + self._rng.uniform(-4, 4),
                y=py + self._rng.uniform(-4, 4),
                vx=vx,
                vy=vy,
                life=life,
                color=color,
            ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _move_player(self, dx: int, dy: int) -> None:
        nx = self.player_x + dx
        ny = self.player_y + dy
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            return
        if self._is_rock(nx, ny):
            return
        self.player_x = nx
        self.player_y = ny
        if self._is_dirt(nx, ny):
            self._dig(nx, ny)

    def _update_enemies(self) -> None:
        move_interval = max(4, ENEMY_MOVE_INTERVAL_BASE - (self.level - 1) * 2)
        for enemy in self.enemies:
            enemy.move_timer += 1
            if enemy.move_timer >= move_interval:
                enemy.move_timer = 0
                self._move_enemy(enemy)

    def _move_enemy(self, enemy: Enemy) -> None:
        directions = ((0, -1), (0, 1), (-1, 0), (1, 0))
        valid_moves: list[tuple[int, int]] = []
        for dx, dy in directions:
            nx, ny = enemy.x + dx, enemy.y + dy
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                continue
            if not self._is_empty(nx, ny):
                continue
            if self._is_rock(nx, ny):
                continue
            if any(e is not enemy and e.x == nx and e.y == ny for e in self.enemies):
                continue
            valid_moves.append((nx, ny))
        if not valid_moves:
            return
        if self._rng.random() < 0.8:
            valid_moves.sort(key=lambda m: abs(m[0] - self.player_x) + abs(m[1] - self.player_y))
            enemy.x, enemy.y = valid_moves[0]
        else:
            enemy.x, enemy.y = self._rng.choice(valid_moves)

    def _update_rocks(self) -> None:
        for rock in self.rocks[:]:
            below = rock.y + 1
            if below >= ROWS:
                self.rocks.remove(rock)
                continue
            supported = self._is_dirt(rock.x, below) or any(
                r is not rock and r.x == rock.x and r.y == below for r in self.rocks
            )
            if not supported:
                rock.falling = True
            if rock.falling:
                rock.fall_timer += 1
                if rock.fall_timer >= ROCK_FALL_FRAMES:
                    rock.fall_timer = 0
                    rock.y += 1
                    if rock.x == self.player_x and rock.y == self.player_y:
                        self._player_hit()
                    for enemy in self.enemies[:]:
                        if rock.x == enemy.x and rock.y == enemy.y:
                            self.enemies.remove(enemy)
                            self.score += 200
                            self._spawn_particles(enemy.x, enemy.y, pyxel.COLOR_ORANGE, 8)
                    new_below = rock.y + 1
                    if new_below >= ROWS:
                        self.rocks.remove(rock)
                    elif self._is_dirt(rock.x, new_below) or any(
                        r is not rock and r.x == rock.x and r.y == new_below for r in self.rocks
                    ):
                        rock.falling = False

    def _player_hit(self) -> None:
        if self.invuln_timer > 0:
            return
        self.lives -= 1
        self.invuln_timer = INVULN_FRAMES
        self.combo = 0
        self.last_dug_color = None
        self._spawn_particles(self.player_x, self.player_y, pyxel.COLOR_RED, 12)
        if self.lives <= 0:
            self.phase = "game_over"

    def _check_enemy_collision(self) -> None:
        if self.invuln_timer > 0:
            return
        for enemy in self.enemies:
            if enemy.x == self.player_x and enemy.y == self.player_y:
                self._player_hit()
                return

    def _handle_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self._move_player(-1, 0)
        elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self._move_player(1, 0)
        elif pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self._move_player(0, -1)
        elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self._move_player(0, 1)

    def update(self) -> None:
        if self.phase == "title":
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = "playing"
        elif self.phase == "playing":
            self._handle_input()
            self._update_enemies()
            self._update_rocks()
            self._update_particles()
            self._check_enemy_collision()
            if self.invuln_timer > 0:
                self.invuln_timer -= 1
            if len(self.enemies) == 0:
                self.phase = "level_clear"
                self.level_clear_timer = LEVEL_CLEAR_FRAMES
            if self.player_x == COLS // 2 and self.player_y == 1:
                self.invuln_timer = max(self.invuln_timer, 30)
        elif self.phase == "level_clear":
            self._update_particles()
            self._update_rocks()
            self.level_clear_timer -= 1
            if self.level_clear_timer <= 0:
                self.level += 1
                self._generate_level()
                self.phase = "playing"
        elif self.phase == "game_over":
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = "playing"

    def _draw_grid(self) -> None:
        for y in range(ROWS):
            for x in range(COLS):
                px = x * CELL
                py = y * CELL
                if self._is_dirt(x, y):
                    color = self.grid[y][x]
                    pyxel.rect(px, py, CELL, CELL, DIRT_COLORS[color])
                    pyxel.rectb(px, py, CELL, CELL, pyxel.COLOR_BLACK)
                elif self._is_empty(x, y):
                    pyxel.rect(px, py, CELL, CELL, pyxel.COLOR_NAVY)

    def _draw_player(self) -> None:
        if self.phase == "game_over":
            return
        if self.invuln_timer > 0 and (pyxel.frame_count // 3) % 2 == 0:
            return
        px = self.player_x * CELL + CELL // 2
        py = self.player_y * CELL + CELL // 2
        size = 12
        pyxel.rect(px - size // 2, py - size // 2, size, size, pyxel.COLOR_WHITE)
        eye_c = pyxel.COLOR_BLACK
        pyxel.rect(px - 3, py - 2, 2, 2, eye_c)
        pyxel.rect(px + 2, py - 2, 2, 2, eye_c)

    def _draw_enemies(self) -> None:
        for enemy in self.enemies:
            px = enemy.x * CELL + CELL // 2
            py = enemy.y * CELL + CELL // 2
            size = 10
            pyxel.rect(px - size // 2, py - size // 2, size, size, pyxel.COLOR_ORANGE)
            eye_c = pyxel.COLOR_BLACK
            pyxel.rect(px - 3, py - 2, 2, 2, eye_c)
            pyxel.rect(px + 2, py - 2, 2, 2, eye_c)

    def _draw_rocks(self) -> None:
        for rock in self.rocks:
            px = rock.x * CELL + CELL // 2
            py = rock.y * CELL + CELL // 2
            size = 14
            pyxel.rect(px - size // 2, py - size // 2, size, size, pyxel.COLOR_GRAY)
            pyxel.rectb(px - size // 2, py - size // 2, size, size, pyxel.COLOR_BROWN)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha_shift = max(0, (22 - p.life) // 3)
            draw_color = p.color
            if alpha_shift > 0 and p.color == pyxel.COLOR_WHITE:
                draw_color = pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), draw_color)

    def _draw_hud(self) -> None:
        hud_y = ROWS * CELL + 2
        pyxel.text(2, hud_y, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)
        pyxel.text(110, hud_y, f"COMBO:{self.combo}", pyxel.COLOR_YELLOW)
        hearts = "O" * self.lives + "-" * (MAX_LIVES - self.lives)
        pyxel.text(200, hud_y, hearts, pyxel.COLOR_RED)
        pyxel.text(270, hud_y, f"Lv{self.level}", pyxel.COLOR_WHITE)

    def _draw_title(self) -> None:
        pyxel.text(80, 60, "CHROMA DIG", pyxel.COLOR_YELLOW)
        pyxel.text(52, 90, "PRESS ENTER TO START", pyxel.COLOR_WHITE)
        pyxel.text(40, 130, "ARROW / WASD : MOVE & DIG", pyxel.COLOR_CYAN)
        for i in range(4):
            cx = 60 + i * 50
            pyxel.rect(cx, 110, 40, 8, DIRT_COLORS[i])
        pyxel.text(40, 150, "DIG SAME COLOR -> COMBO UP", pyxel.COLOR_GREEN)
        pyxel.text(40, 162, "CONNECT TUNNELS -> CHAIN BONUS", pyxel.COLOR_GREEN)
        pyxel.text(40, 174, "ROCKS KILL ENEMIES (+200pts)", pyxel.COLOR_GREEN)
        pyxel.rect(150, 200, 4, 4, pyxel.COLOR_WHITE)
        pyxel.rect(176, 200, 4, 4, pyxel.COLOR_ORANGE)
        pyxel.text(158, 200, "YOU", pyxel.COLOR_WHITE)
        pyxel.text(184, 200, "ENEMY", pyxel.COLOR_ORANGE)

    def _draw_game_over(self) -> None:
        pyxel.text(100, 50, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(60, 72, f"FINAL SCORE: {self.score:06d}", pyxel.COLOR_WHITE)
        pyxel.text(60, 86, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(60, 100, f"LEVEL: {self.level}", pyxel.COLOR_WHITE)
        pyxel.text(68, 130, "PRESS R TO RETRY", pyxel.COLOR_CYAN)

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        if self.phase in ("playing", "level_clear", "player_hit"):
            self._draw_grid()
            self._draw_rocks()
            self._draw_enemies()
            self._draw_player()
            self._draw_particles()
            self._draw_hud()
            if self.phase == "level_clear":
                pyxel.text(105, 100, "LEVEL CLEAR!", pyxel.COLOR_YELLOW)
        elif self.phase == "title":
            self._draw_title()
        elif self.phase == "game_over":
            self._draw_grid()
            self._draw_rocks()
            self._draw_enemies()
            self._draw_player()
            self._draw_particles()
            self._draw_hud()
            self._draw_game_over()


class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="Chroma Dig", display_scale=2)
        self.game = Game()
        pyxel.run(self.game.update, self.game.draw)


if __name__ == "__main__":
    App()
