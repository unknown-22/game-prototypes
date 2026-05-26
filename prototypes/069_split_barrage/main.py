"""069_split_barrage — Split-Converge Artillery.

Core fun moment: firing a projectile and splitting it at the best timing,
watching same-color fragments cluster on the grid and chain-explode
for massive cascade score.
Risk/reward: split early for wider spread vs. split late for precision,
power tradeoff between high spread count vs. column overflow risk.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 30

GRID_COLS = 16
GRID_ROWS = 5
CELL = 20
GRID_Y = 200

CANNON_X = 160
CANNON_Y = 220

SHOTS_TOTAL = 10
GRAVITY = 0.15
FRAGMENT_GRAVITY = 0.1
FRAGMENT_COLORS: tuple[int, int, int, int] = (8, 9, 10, 12)  # RED, ORANGE, YELLOW, CYAN
MIN_CLUSTER = 3

POWER_MIN = 1.0
POWER_MAX = 20.0
ANGLE_MIN = 30.0
ANGLE_MAX = 80.0

SCORE_PER_CELL = 10

# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    SPLITTING = auto()
    RESOLVING = auto()
    GAME_OVER = auto()


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Fragment:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    landed: bool = False
    grid_col: int = -1
    grid_row: int = -1


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class ComboText:
    x: float
    y: float
    life: int
    text: str
    color: int


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Split Barrage", display_scale=DISPLAY_SCALE, fps=FPS)
        pyxel.mouse(True)
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        pyxel.load(font_path, exclude_images=False, exclude_tilemaps=False, exclude_sounds=False, exclude_musics=False)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_multiplier: float = 1.0
        self.shots_used: int = 0
        self.grid: list[list[int]] = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
        self.fragments: list[Fragment] = []
        self.particles: list[Particle] = []
        self.combo_texts: list[ComboText] = []
        self.projectile_x: float = 0.0
        self.projectile_y: float = 0.0
        self.projectile_vx: float = 0.0
        self.projectile_vy: float = 0.0
        self.projectile_active: bool = False
        self.aim_angle: float = 60.0
        self.aim_power: float = 8.0
        self.is_aiming: bool = False
        self.aim_start_x: int = 0
        self.aim_start_y: int = 0
        self._prev_mouse: bool = False
        self._resolve_state: str = "wait"  # "wait" | "finding" | "gravity" | "done"
        self._resolve_clusters: list[set[tuple[int, int]]] = []
        self._resolve_cluster_idx: int = 0
        self._resolve_cell_delay: int = 0
        self._resolve_cells: list[tuple[int, int]] = []
        self._resolve_anim_frame: int = 0
        self._flash_timer: int = 0

    # ── Pure Logic: BFS Cluster Detection ──────────────────────────

    @staticmethod
    def _bfs_cluster(
        grid: list[list[int]],
        start_col: int,
        start_row: int,
    ) -> set[tuple[int, int]]:
        rows = len(grid)
        cols = len(grid[0])
        color = grid[start_row][start_col]
        if color == 0:
            return set()

        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = [(start_col, start_row)]
        visited.add((start_col, start_row))

        while stack:
            c, r = stack.pop()
            for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nc, nr = c + dc, r + dr
                if 0 <= nc < cols and 0 <= nr < rows:
                    if (nc, nr) not in visited and grid[nr][nc] == color:
                        visited.add((nc, nr))
                        stack.append((nc, nr))

        return visited

    @staticmethod
    def _find_all_clusters(
        grid: list[list[int]],
    ) -> list[set[tuple[int, int]]]:
        rows = len(grid)
        cols = len(grid[0])
        found: list[set[tuple[int, int]]] = []
        seen: set[tuple[int, int]] = set()

        for r in range(rows):
            for c in range(cols):
                if grid[r][c] != 0 and (c, r) not in seen:
                    cluster = Game._bfs_cluster(grid, c, r)
                    if len(cluster) >= MIN_CLUSTER:
                        found.append(cluster)
                    seen.update(cluster)

        found.sort(key=len, reverse=True)
        return found

    # ── Pure Logic: Gravity Compaction ─────────────────────────────

    @staticmethod
    def _apply_gravity(grid: list[list[int]]) -> bool:
        rows = len(grid)
        cols = len(grid[0])
        moved = False

        for c in range(cols):
            write_r = rows - 1
            for r in range(rows - 1, -1, -1):
                if grid[r][c] != 0:
                    if r != write_r:
                        grid[write_r][c] = grid[r][c]
                        grid[r][c] = 0
                        moved = True
                    write_r -= 1

        return moved

    # ── Fragment Spawning ──────────────────────────────────────────

    def _spawn_fragments(self, x: float, y: float, power: float) -> list[Fragment]:
        count = int(5 + (power / POWER_MAX) * 2)
        count = max(5, min(7, count))
        base_speed = 1.5 + power * 0.3

        fragments: list[Fragment] = []
        colors_pool = list(FRAGMENT_COLORS)
        self._rng.shuffle(colors_pool)
        angles: list[float] = []

        if count <= 1:
            angles = [0.0]
        else:
            spread_deg = 60.0 + (power / POWER_MAX) * 60.0
            for i in range(count):
                angle = -spread_deg / 2 + i * spread_deg / (count - 1)
                angles.append(angle)

        for i, deg in enumerate(angles):
            rad = math.radians(deg)
            color = colors_pool[i % len(colors_pool)]
            speed_jitter = base_speed * (0.8 + self._rng.random() * 0.4)
            fragments.append(Fragment(
                x=float(x),
                y=float(y),
                vx=math.cos(rad) * speed_jitter,
                vy=math.sin(rad) * speed_jitter,
                color=color,
            ))

        return fragments

    # ── Fragment Landing ───────────────────────────────────────────

    def _resolve_landing(self, frag: Fragment) -> bool:
        col = int(frag.x // CELL)
        if col < 0 or col >= GRID_COLS:
            return False

        for row in range(GRID_ROWS - 1, -1, -1):
            if self.grid[row][col] == 0:
                self.grid[row][col] = frag.color
                frag.grid_col = col
                frag.grid_row = row
                frag.landed = True
                return True

        return False

    # ── Particle / Combo Text ─────────────────────────────────────

    def _spawn_explosion(self, col: int, row: int, color: int) -> None:
        cx = col * CELL + CELL / 2
        cy = GRID_Y + row * CELL + CELL / 2
        for _ in range(8):
            angle = self._rng.random() * math.pi * 2
            speed = 1.0 + self._rng.random() * 2.5
            self.particles.append(Particle(
                x=float(cx),
                y=float(cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15 + self._rng.randint(0, 5),
                color=color,
            ))

    def _spawn_combo_text(self, col: int, row: int, cs: int, cmul: float) -> None:
        cx = col * CELL + CELL / 2
        cy = GRID_Y + row * CELL
        self.combo_texts.append(ComboText(
            x=float(cx),
            y=float(cy),
            life=30,
            text=f"x{cs}",
            color=10 if cs < 5 else 8,
        ))

    # ── Resolution: Chain Reaction ────────────────────────────────

    def _check_and_resolve(self) -> int:
        total = 0
        while True:
            clusters = self._find_all_clusters(self.grid)
            if not clusters:
                break

            for cluster in clusters:
                cs = len(cluster)
                points = int(cs * cs * self.combo_multiplier * SCORE_PER_CELL)
                total += points
                self.score += points
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                self.combo_multiplier = 1.0 + (self.combo - 1) * 0.5

                for c, r in cluster:
                    color = self.grid[r][c]
                    self.grid[r][c] = 0
                    self._spawn_explosion(c, r, color)

                if cluster:
                    first = next(iter(cluster))
                    self._spawn_combo_text(first[0], first[1], cs, self.combo_multiplier)

            if not self._apply_gravity(self.grid):
                return total

        return total

    # ── Resolution: Animated Step-by-Step ─────────────────────────

    def _resolve_step(self) -> bool:
        """Process one step of animated chain resolution. Returns True when done."""
        if self._resolve_state == "wait":
            clusters = self._find_all_clusters(self.grid)
            if not clusters:
                self._resolve_state = "done"
                self.combo = 0
                self.combo_multiplier = 1.0
                return True

            self._resolve_clusters = clusters
            self._resolve_cluster_idx = 0
            self._resolve_cells = []
            self._resolve_cell_delay = 3
            self._resolve_anim_frame = 0
            self._resolve_state = "finding"
            return False

        if self._resolve_state == "finding":
            if self._resolve_cluster_idx >= len(self._resolve_clusters):
                self.combo += len(self._resolve_clusters)
                self._resolve_state = "gravity"
                self._resolve_anim_frame = 0
                return False

            if not self._resolve_cells:
                cluster = self._resolve_clusters[self._resolve_cluster_idx]
                self._resolve_cells = list(cluster)
                self._resolve_cell_delay = 3

            if self._resolve_cell_delay > 0:
                self._resolve_cell_delay -= 1
                return False

            c, r = self._resolve_cells.pop(0)
            color = self.grid[r][c]
            if color != 0:
                self.grid[r][c] = 0
                cs = len(self._resolve_clusters[self._resolve_cluster_idx])
                points = int(cs * cs * self.combo_multiplier * SCORE_PER_CELL)
                self.score += points
                if self.combo + 1 > self.max_combo:
                    self.max_combo = self.combo + 1
                self._spawn_explosion(c, r, color)

            if not self._resolve_cells:
                cluster = self._resolve_clusters[self._resolve_cluster_idx]
                first = next(iter(cluster))
                cs = len(cluster)
                self._spawn_combo_text(first[0], first[1], cs, self.combo_multiplier)
                self._resolve_cluster_idx += 1

            return False

        if self._resolve_state == "gravity":
            self._resolve_anim_frame += 1
            if self._resolve_anim_frame < 5:
                return False
            moved = self._apply_gravity(self.grid)
            if not moved:
                self._resolve_state = "wait"
                return self._resolve_step()
            self._resolve_state = "wait"
            return False

        if self._resolve_state == "done":
            self.combo = 0
            self.combo_multiplier = 1.0
            return True

        return False

    # ── Update ─────────────────────────────────────────────────────

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _update_aiming(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.is_aiming = True
            self.aim_start_x = mx
            self.aim_start_y = my

        if self.is_aiming and pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            dx = float(mx - self.aim_start_x)
            dy = float(my - self.aim_start_y)
            self.aim_power = max(POWER_MIN, min(POWER_MAX, abs(dx) * 0.1))
            raw_angle = 45.0 - dy * 0.2
            self.aim_angle = max(ANGLE_MIN, min(ANGLE_MAX, raw_angle))
            return

        if self.is_aiming and not pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            self.is_aiming = False
            rad = math.radians(self.aim_angle)
            self.projectile_vx = math.cos(rad) * self.aim_power * 1.5
            self.projectile_vy = -math.sin(rad) * self.aim_power * 1.5
            self.projectile_x = float(CANNON_X)
            self.projectile_y = float(CANNON_Y)
            self.projectile_active = True
            if self._rng.random() < 0.5:
                self.projectile_vx = -self.projectile_vx
            self.shots_used += 1
            self.phase = Phase.FLYING

    def _update_flying(self) -> None:
        self.projectile_vy += GRAVITY
        self.projectile_x += self.projectile_vx
        self.projectile_y += self.projectile_vy

        if (self.projectile_x < -20 or self.projectile_x > SCREEN_W + 20
                or self.projectile_y > SCREEN_H + 20 or self.projectile_y < -100):
            self.projectile_active = False
            self._start_aiming()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
            self.split_projectile()
            return

    def _update_splitting(self) -> None:
        all_landed = True
        for frag in self.fragments:
            if frag.landed:
                continue
            frag.vy += FRAGMENT_GRAVITY
            frag.x += frag.vx
            frag.y += frag.vy

            if frag.x < 0:
                frag.x = 0
                frag.vx *= -0.4
            if frag.x > SCREEN_W - 1:
                frag.x = SCREEN_W - 1
                frag.vx *= -0.4

            if frag.y >= GRID_Y:
                self._resolve_landing(frag)
                if not frag.landed:
                    frag.landed = True

        for frag in self.fragments:
            if not frag.landed:
                all_landed = False
                break

        if all_landed:
            self.fragments.clear()
            self.phase = Phase.RESOLVING
            self._resolve_state = "wait"
            self._resolve_clusters = []
            self._resolve_cluster_idx = 0
            self._resolve_cells = []
            self._resolve_cell_delay = 0
            self._resolve_anim_frame = 0

    def _update_resolving(self) -> None:
        done = self._resolve_step()
        if done:
            if self.shots_used >= SHOTS_TOTAL:
                self.phase = Phase.GAME_OVER
            else:
                self._start_aiming()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def update(self) -> None:
        self._update_particles()
        self._update_combo_texts()
        if self._flash_timer > 0:
            self._flash_timer -= 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.FLYING:
            self._update_flying()
        elif self.phase == Phase.SPLITTING:
            self._update_splitting()
        elif self.phase == Phase.RESOLVING:
            self._update_resolving()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    # ── Drawing ─────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(0)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_grid()
        self._draw_fragments()
        self._draw_cannon()

        if self.phase == Phase.AIMING and self.is_aiming:
            self._draw_trajectory()

        if self.phase == Phase.FLYING and self.projectile_active:
            self._draw_projectile()

        self._draw_particles()
        self._draw_combo_texts()
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.AIMING and not self.is_aiming:
            self._draw_aim_instruction()

    def _draw_title(self) -> None:
        title = "SPLIT BARRAGE"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 40, title, pyxel.COLOR_WHITE)

        lines = [
            "Click & drag: aim + power",
            "Release: fire projectile",
            "Click mid-air: SPLIT!",
            "Match 3+ same-color:",
            "  CHAIN EXPLODE!",
            "",
            "Click to Start",
        ]
        for i, line in enumerate(lines):
            if line:
                pyxel.text(SCREEN_W // 2 - len(line) * 4 // 2, 75 + i * 14, line, pyxel.COLOR_GRAY)

    def _draw_aim_instruction(self) -> None:
        hint = "Click & drag to aim"
        pyxel.text(SCREEN_W // 2 - len(hint) * 4 // 2, 10, hint, pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, 50, 140, 110, 5)
        pyxel.text(SCREEN_W // 2 - len("GAME OVER") * 4 // 2, 60, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 45, 85, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 50, 105, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_ORANGE)
        pyxel.text(SCREEN_W // 2 - len("Click to Retry") * 4 // 2, 140, "Click to Retry", pyxel.COLOR_WHITE)

    def _draw_grid(self) -> None:
        for r in range(GRID_ROWS + 1):
            y = GRID_Y + r * CELL
            pyxel.line(0, y, SCREEN_W, y, 5)
        for c in range(GRID_COLS + 1):
            x = c * CELL
            pyxel.line(x, GRID_Y, x, GRID_Y + GRID_ROWS * CELL, 5)

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                color = self.grid[r][c]
                if color != 0:
                    px = c * CELL + 1
                    py = GRID_Y + r * CELL + 1
                    pyxel.rect(px, py, CELL - 2, CELL - 2, color)
                    pyxel.rectb(px, py, CELL - 2, CELL - 2, 7)

    def _draw_cannon(self) -> None:
        cx, cy = CANNON_X, CANNON_Y
        pyxel.rect(cx - 8, cy, 16, 12, 13)
        pyxel.rect(cx - 14, cy + 8, 28, 6, 13)
        pyxel.circ(cx, cy + 14, 6, 13)

        if self.phase == Phase.AIMING and self.is_aiming:
            rad = math.radians(self.aim_angle)
            barrel_len = 25.0
            bx = cx + math.cos(rad) * barrel_len
            by = cy + math.sin(rad) * barrel_len
            pyxel.line(cx, cy, int(bx), int(by), 7)

    def _draw_trajectory(self) -> None:
        rad = math.radians(self.aim_angle)
        vx = math.cos(rad) * self.aim_power * 1.5
        vy = -math.sin(rad) * self.aim_power * 1.5
        px_val = float(CANNON_X)
        py_val = float(CANNON_Y)
        for _ in range(60):
            px_val += vx
            py_val += vy
            vy += GRAVITY
            if px_val < 0 or px_val > SCREEN_W or py_val > SCREEN_H or py_val < 0:
                break
            pyxel.pset(int(px_val), int(py_val), 8)

    def _draw_projectile(self) -> None:
        pyxel.circb(int(self.projectile_x), int(self.projectile_y), 3, 7)

    def _draw_fragments(self) -> None:
        for frag in self.fragments:
            if not frag.landed and frag.y < GRID_Y:
                pyxel.circb(int(frag.x), int(frag.y), 2, frag.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_combo_texts(self) -> None:
        for ct in self.combo_texts:
            pyxel.text(int(ct.x), int(ct.y), ct.text, ct.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 18, 0)
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(64, 4, f"COMBO: {self.combo} x{self.combo_multiplier:.1f}", pyxel.COLOR_ORANGE)
        shots_left = SHOTS_TOTAL - self.shots_used
        pyxel.text(SCREEN_W // 2 - 30, 4, f"SHOTS: {shots_left}", pyxel.COLOR_WHITE)

    # ── Particle / Combo Text Updates ───────────────────────────────

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_combo_texts(self) -> None:
        for ct in self.combo_texts[:]:
            ct.y -= 0.5
            ct.life -= 1
            if ct.life <= 0:
                self.combo_texts.remove(ct)

    # ── Transitions ─────────────────────────────────────────────────

    def split_projectile(self) -> None:
        self.fragments = self._spawn_fragments(
            self.projectile_x,
            self.projectile_y,
            self.aim_power,
        )
        self.projectile_active = False
        self.phase = Phase.SPLITTING

    def _start_aiming(self) -> None:
        self.phase = Phase.AIMING
        self.projectile_active = False
        self.is_aiming = False
        self.fragments.clear()
        self.particles.clear()
        self.combo_texts.clear()

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_multiplier = 1.0
        self.shots_used = 0
        self.grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
        self.fragments.clear()
        self.particles.clear()
        self.combo_texts.clear()
        self.projectile_active = False
        self.is_aiming = False
        self._resolve_state = "wait"
        self._resolve_clusters = []
        self._resolve_cluster_idx = 0
        self._resolve_cells = []
        self._resolve_cell_delay = 0
        self._resolve_anim_frame = 0
        self.phase = Phase.AIMING


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
