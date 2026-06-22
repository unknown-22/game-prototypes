from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Color constants ──────────────────────────────────────────────────
BLACK, NAVY, PURPLE, GREEN, BROWN, DARK_BLUE, LIGHT_BLUE = 0, 1, 2, 3, 4, 5, 6
WHITE, RED, ORANGE, YELLOW, LIME, CYAN, GRAY, PINK, PEACH = 7, 8, 9, 10, 11, 12, 13, 14, 15

TARGET_COLORS = [RED, GREEN, CYAN, YELLOW]
RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE, PINK]

# ── Tuning constants ─────────────────────────────────────────────────
PLAYER_SPEED = 2.0
PLAYER_RADIUS = 6
TARGET_RADIUS = 5
PAINTBALL_RADIUS = 3.0
PAINTBALL_SPEED = 6.0
HEAT_MAX = 100.0
GAME_DURATION = 90.0
SUPER_DURATION = 5.0
SHOOT_COOLDOWN = 9
SPREAD_INTERVAL = 15
SUPER_AUTO_FIRE_INTERVAL = 6
HEAT_PER_WRONG = 15.0
HEAT_PER_ESCAPE = 5.0
HEAT_DECAY_PER_FRAME = 0.5 / 30.0
SPAWN_INTERVAL_MIN = 45
SPAWN_INTERVAL_MAX = 90
SPREAD_CHANCE = 0.3
SPEED_MULT_RATE = 0.0003


# ── Enums & Data ─────────────────────────────────────────────────────
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Target:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    hp: int = 1


@dataclass
class Paintball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    radius: float = PAINTBALL_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    radius: float = 2.0


# ── Game ─────────────────────────────────────────────────────────────
class Game:
    CELL = 16
    GRID_COLS = 18
    GRID_ROWS = 13
    OFFSET_X = 16
    OFFSET_Y = 16
    ARENA_W = GRID_COLS * CELL
    ARENA_H = GRID_ROWS * CELL
    SCREEN_W = 320
    SCREEN_H = 240

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, "PAINT SURGE", display_scale=2)
        self._setup_sounds()
        self.rng = random.Random()
        self.previous_grid: list[list[int]] | None = None
        self.prev_score: int = 0
        self.prev_max_combo: int = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def _setup_sounds(self) -> None:
        pyxel.sounds[0].set("c3e3g3", "p", "5", "f", 8)   # shoot
        pyxel.sounds[1].set("c4", "n", "7", "f", 5)         # hit
        pyxel.sounds[2].set("c4e4g4c5", "p", "5", "f", 15)  # super activate
        pyxel.sounds[3].set("g2c2", "p", "7", "f", 20)      # game over

    # ── State ──────────────────────────────────────────────────────
    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: float = GAME_DURATION
        self.player_x: float = self.OFFSET_X + self.ARENA_W / 2
        self.player_y: float = self.OFFSET_Y + self.ARENA_H / 2
        self.aim_x: float = self.player_x
        self.aim_y: float = self.player_y
        self.color_idx: int = 0
        self.cooldown: int = 0
        self.super_timer: float = 0.0
        self.was_super: bool = False
        self.paint_grid: list[list[int]] = [
            [-1] * self.GRID_COLS for _ in range(self.GRID_ROWS)
        ]
        self.targets: list[Target] = []
        self.paintballs: list[Paintball] = []
        self.particles: list[Particle] = []
        self.spawn_timer: float = float(SPAWN_INTERVAL_MIN)
        self.spread_counter: int = 0
        self.frame: int = 0
        self.super_fire_counter: int = 0
        self.rainbow_index: int = 0
        self.speed_multiplier: float = 1.0
        if not hasattr(self, "previous_grid"):
            self.previous_grid = None
            self.prev_score = 0
            self.prev_max_combo = 0

    # ── Update / Draw dispatch ─────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ── TITLE ──────────────────────────────────────────────────────
    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        pyxel.text(120, 36, "PAINT SURGE", WHITE)
        pyxel.text(108, 48, "PAINTBALL ARENA", GRAY)
        pyxel.text(76, 80, "Click or SPACE to start", WHITE)
        pyxel.text(56, 100, "WASD: Move  Mouse: Aim  Click: Shoot", GRAY)
        pyxel.text(88, 116, "Match colors for COMBO chain!", GRAY)
        pyxel.text(84, 132, "COMBO x5 = SUPER SHOT!", YELLOW)
        pyxel.text(92, 148, "HEAT >= 100 = GAME OVER", ORANGE)
        pyxel.text(88, 164, "Survive 90s to VICTORY!", LIME)
        self._draw_ghost_grid()

    # ── PLAYING (wrapper: calls pyxel input, delegates to pure logic) ─
    def _update_playing(self) -> None:
        self.frame += 1
        self._handle_input()
        self._update_cooldown()
        self._update_targets()
        self._update_paintballs()
        self._check_hits()
        self._update_super()
        self._update_paint_spread()
        self._update_particles()
        self._update_heat_decay()
        self._update_spawning()
        self._update_speed_multiplier()
        self.game_timer -= 1.0 / 30.0
        self._check_game_over()

    def _handle_input(self) -> None:
        speed = self._current_speed()
        if pyxel.btn(pyxel.KEY_W):
            self.player_y -= speed
        if pyxel.btn(pyxel.KEY_S):
            self.player_y += speed
        if pyxel.btn(pyxel.KEY_A):
            self.player_x -= speed
        if pyxel.btn(pyxel.KEY_D):
            self.player_x += speed
        self.player_x = max(
            self.OFFSET_X + PLAYER_RADIUS,
            min(self.OFFSET_X + self.ARENA_W - PLAYER_RADIUS, self.player_x),
        )
        self.player_y = max(
            self.OFFSET_Y + PLAYER_RADIUS,
            min(self.OFFSET_Y + self.ARENA_H - PLAYER_RADIUS, self.player_y),
        )
        self.aim_x = float(pyxel.mouse_x)
        self.aim_y = float(pyxel.mouse_y)
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.cooldown <= 0:
            self._shoot(self.aim_x, self.aim_y)

    def _update_cooldown(self) -> None:
        if self.cooldown > 0:
            self.cooldown -= 1

    def _current_speed(self) -> float:
        gx = int((self.player_x - self.OFFSET_X) // self.CELL)
        gy = int((self.player_y - self.OFFSET_Y) // self.CELL)
        if 0 <= gx < self.GRID_COLS and 0 <= gy < self.GRID_ROWS:
            c = self.paint_grid[gy][gx]
            if c >= 0:
                if c == self.color_idx:
                    return PLAYER_SPEED * 1.3
                else:
                    return PLAYER_SPEED * 0.7
        return PLAYER_SPEED

    # ── Core logic (testable — no pyxel input calls) ──────────────
    def _spawn_target(self) -> None:
        color = self.rng.randint(0, 3)
        speed = self.rng.uniform(0.5, 2.0) * self.speed_multiplier
        side = self.rng.randint(0, 3)
        cx = self.OFFSET_X + self.ARENA_W / 2
        cy = self.OFFSET_Y + self.ARENA_H / 2
        if side == 0:
            x = self.rng.uniform(self.OFFSET_X, self.OFFSET_X + self.ARENA_W)
            y = float(self.OFFSET_Y - 10)
        elif side == 1:
            x = self.rng.uniform(self.OFFSET_X, self.OFFSET_X + self.ARENA_W)
            y = float(self.OFFSET_Y + self.ARENA_H + 10)
        elif side == 2:
            x = float(self.OFFSET_X - 10)
            y = self.rng.uniform(self.OFFSET_Y, self.OFFSET_Y + self.ARENA_H)
        else:
            x = float(self.OFFSET_X + self.ARENA_W + 10)
            y = self.rng.uniform(self.OFFSET_Y, self.OFFSET_Y + self.ARENA_H)
        angle = math.atan2(cy - y, cx - x) + self.rng.uniform(-0.5, 0.5)
        self.targets.append(Target(x, y, math.cos(angle) * speed, math.sin(angle) * speed, color))

    def _update_targets(self) -> None:
        margin: float = 20.0
        alive: list[Target] = []
        for t in self.targets:
            nx = t.x + t.vx
            ny = t.y + t.vy
            if (
                nx < self.OFFSET_X - margin
                or nx > self.OFFSET_X + self.ARENA_W + margin
                or ny < self.OFFSET_Y - margin
                or ny > self.OFFSET_Y + self.ARENA_H + margin
            ):
                self.heat += HEAT_PER_ESCAPE
            else:
                t.x = nx
                t.y = ny
                alive.append(t)
        self.targets = alive

    def _shoot(self, tx: float, ty: float) -> None:
        dx = tx - self.player_x
        dy = ty - self.player_y
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            dx, dy, dist = 0.0, -1.0, 1.0
        vx = (dx / dist) * PAINTBALL_SPEED
        vy = (dy / dist) * PAINTBALL_SPEED
        self.paintballs.append(Paintball(self.player_x, self.player_y, vx, vy, self.color_idx))
        self.color_idx = (self.color_idx + 1) % 4
        self.cooldown = SHOOT_COOLDOWN
        pyxel.play(0, 0)

    def _update_paintballs(self) -> None:
        alive: list[Paintball] = []
        for b in self.paintballs:
            b.x += b.vx
            b.y += b.vy
            if 0 <= b.x <= self.SCREEN_W and 0 <= b.y <= self.SCREEN_H:
                alive.append(b)
        self.paintballs = alive

    def _check_hits(self) -> None:
        balls_to_remove: list[Paintball] = []
        for b in self.paintballs:
            hit: Target | None = None
            for t in self.targets:
                if t.hp <= 0:
                    continue
                if math.hypot(b.x - t.x, b.y - t.y) < b.radius + TARGET_RADIUS:
                    hit = t
                    break
            if hit is not None:
                self._register_hit(hit, b.color)
                hit.hp = 0
                balls_to_remove.append(b)
        for b in balls_to_remove:
            if b in self.paintballs:
                self.paintballs.remove(b)
        self.targets = [t for t in self.targets if t.hp > 0]

    def _register_hit(self, target: Target, color: int) -> None:
        is_match = target.color == color
        if self.super_timer > 0 or is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = 10 * self.combo
            if self.super_timer > 0:
                points *= 3
            self.score += points
            self._splash_paint(target.x, target.y, color)
            self._add_particles(target.x, target.y, TARGET_COLORS[target.color], 8)
            pyxel.play(1, 1)
            if self.combo >= 5 and self.super_timer <= 0:
                self._activate_super()
        else:
            self.combo = 0
            self.heat += HEAT_PER_WRONG
            self._add_particles(target.x, target.y, ORANGE, 4)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.super_fire_counter = 0
        self.was_super = True
        self._add_particles(self.player_x, self.player_y, YELLOW, 20)
        pyxel.play(2, 2)

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1.0 / 30.0
            self.rainbow_index = (self.rainbow_index + 1) % len(RAINBOW_COLORS)
            self.super_fire_counter += 1
            if self.super_fire_counter >= SUPER_AUTO_FIRE_INTERVAL and self.targets:
                self.super_fire_counter = 0
                nearest = min(
                    self.targets,
                    key=lambda t: math.hypot(t.x - self.player_x, t.y - self.player_y),
                )
                self._shoot(nearest.x, nearest.y)
            if self.super_timer <= 0:
                self.super_timer = 0.0
                self.was_super = False

    def _splash_paint(self, x: float, y: float, color: int) -> None:
        gx = int((x - self.OFFSET_X) / self.CELL)
        gy = int((y - self.OFFSET_Y) / self.CELL)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx = gx + dx
                ny = gy + dy
                if 0 <= nx < self.GRID_COLS and 0 <= ny < self.GRID_ROWS:
                    self.paint_grid[ny][nx] = color
        self._add_particles(x, y, TARGET_COLORS[color], 4)

    def _update_paint_spread(self) -> None:
        self.spread_counter += 1
        if self.spread_counter < SPREAD_INTERVAL:
            return
        self.spread_counter = 0
        new_grid = [row[:] for row in self.paint_grid]
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                cell = self.paint_grid[row][col]
                if cell < 0:
                    continue
                for dc, dr in dirs:
                    nc, nr = col + dc, row + dr
                    if 0 <= nc < self.GRID_COLS and 0 <= nr < self.GRID_ROWS:
                        if self.paint_grid[nr][nc] < 0 and self.rng.random() < SPREAD_CHANCE:
                            new_grid[nr][nc] = cell
        self.paint_grid = new_grid

    def _add_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            a = self.rng.uniform(0, math.pi * 2)
            s = self.rng.uniform(1, 3)
            life = self.rng.randint(10, 20)
            self.particles.append(
                Particle(x, y, math.cos(a) * s, math.sin(a) * s, life, color)
            )

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                if p.life < 10:
                    p.radius = max(0.2, p.radius - 0.1)
                alive.append(p)
        self.particles = alive

    def _update_heat_decay(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY_PER_FRAME)

    def _update_spawning(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_target()
            self.spawn_timer = float(
                self.rng.randint(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)
            )

    def _update_speed_multiplier(self) -> None:
        self.speed_multiplier = 1.0 + self.frame * SPEED_MULT_RATE

    def _check_game_over(self) -> None:
        if self.heat >= HEAT_MAX or self.game_timer <= 0:
            self.previous_grid = [row[:] for row in self.paint_grid]
            self.prev_score = self.score
            self.prev_max_combo = self.max_combo
            self.phase = Phase.GAME_OVER
            pyxel.play(3, 3)

    # ── GAME OVER ──────────────────────────────────────────────────
    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    def _draw_game_over(self) -> None:
        pyxel.text(120, 28, "GAME OVER", WHITE)
        if self.heat >= HEAT_MAX:
            pyxel.text(108, 40, "HEAT OVERLOAD!", ORANGE)
        else:
            pyxel.text(124, 40, "TIME UP!", LIME)
        pyxel.text(112, 58, f"SCORE: {self.prev_score}", WHITE)
        pyxel.text(100, 72, f"MAX COMBO: {self.prev_max_combo}", YELLOW)
        pyxel.text(84, 94, "Click or SPACE to retry", WHITE)
        self._draw_ghost_grid()

    # ── Shared drawing helpers ─────────────────────────────────────
    def _draw_ghost_grid(self) -> None:
        grid = self.previous_grid
        if grid is None:
            return
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                if grid[row][col] >= 0:
                    c = TARGET_COLORS[grid[row][col]]
                    x = self.OFFSET_X + col * self.CELL
                    y = self.OFFSET_Y + row * self.CELL
                    pyxel.rect(x, y, self.CELL, self.CELL, c)
                    pyxel.rect(x + 2, y + 2, self.CELL - 4, self.CELL - 4, BLACK)

    def _draw_playing(self) -> None:
        # Paint grid
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                v = self.paint_grid[row][col]
                if v >= 0:
                    pyxel.rect(
                        self.OFFSET_X + col * self.CELL,
                        self.OFFSET_Y + row * self.CELL,
                        self.CELL,
                        self.CELL,
                        TARGET_COLORS[v],
                    )
        # Arena border
        pyxel.rectb(self.OFFSET_X - 1, self.OFFSET_Y - 1, self.ARENA_W + 2, self.ARENA_H + 2, WHITE)
        # Targets
        for t in self.targets:
            pyxel.circ(int(t.x), int(t.y), TARGET_RADIUS, TARGET_COLORS[t.color])
            pyxel.circb(int(t.x), int(t.y), TARGET_RADIUS, BLACK)
        # Paintballs
        for b in self.paintballs:
            pyxel.circ(int(b.x), int(b.y), int(b.radius), TARGET_COLORS[b.color])
        # Particles
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), max(1, int(p.radius)), p.color)
        # Player
        px, py = int(self.player_x), int(self.player_y)
        if self.super_timer > 0:
            pcol = RAINBOW_COLORS[self.rainbow_index % len(RAINBOW_COLORS)]
        else:
            pcol = TARGET_COLORS[self.color_idx]
        pyxel.circ(px, py, PLAYER_RADIUS, pcol)
        pyxel.circb(px, py, PLAYER_RADIUS, WHITE)
        pyxel.line(px - 4, py, px + 4, py, WHITE)
        pyxel.line(px, py - 4, px, py + 4, WHITE)
        # Mouse crosshair
        cx, cy = pyxel.mouse_x, pyxel.mouse_y
        pyxel.line(cx - 6, cy, cx - 2, cy, WHITE)
        pyxel.line(cx + 2, cy, cx + 6, cy, WHITE)
        pyxel.line(cx, cy - 6, cx, cy - 2, WHITE)
        pyxel.line(cx, cy + 2, cx, cy + 6, WHITE)
        # SUPER border flash
        if self.super_timer > 0:
            flash = RAINBOW_COLORS[self.rainbow_index % len(RAINBOW_COLORS)]
            pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, flash)
            pyxel.rectb(1, 1, self.SCREEN_W - 2, self.SCREEN_H - 2, flash)
        # ── HUD ──
        self._draw_hud()

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        # Combo (center-top)
        ct = f"COMBO x{self.combo}"
        if self.combo >= 5:
            cc = ORANGE
        elif self.combo >= 3:
            cc = YELLOW
        else:
            cc = WHITE
        pyxel.text(self.SCREEN_W // 2 - len(ct) * 2, 4, ct, cc)
        # Timer (top-right)
        tt = f"TIME: {max(0, int(self.game_timer))}"
        pyxel.text(self.SCREEN_W - len(tt) * 4 - 4, 4, tt, WHITE)
        # SUPER timer
        if self.super_timer > 0:
            st = f"SUPER: {self.super_timer:.1f}s"
            pyxel.text(self.SCREEN_W - len(st) * 4 - 4, 12, st, YELLOW)
        # HEAT bar (vertical, right margin)
        bx, by, bw, bh = 306, 30, 8, 180
        pyxel.rect(bx, by, bw, bh, GRAY)
        heat_h = int((self.heat / HEAT_MAX) * bh)
        if self.heat < 30:
            hc = GREEN
        elif self.heat < 60:
            hc = YELLOW
        elif self.heat < 80:
            hc = ORANGE
        else:
            hc = RED
        pyxel.rect(bx, by + bh - heat_h, bw, heat_h, hc)
        pyxel.rectb(bx, by, bw, bh, WHITE)
        pyxel.text(bx - 8, by - 8, "HEAT", GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
