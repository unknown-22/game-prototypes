"""ECHO STEALTH — Top-down grid stealth prototype.
Reinterpreted from game_idea_factory idea #1 (score 31.85):
  "one-color-per-turn" → one guard color has vision per frequency phase
  "log/replay as asset" → echoes left when caught act as distractions

Goal: Reach the EXIT without being caught by active-color guards.
Collect gems for bonus score. When caught, you leave an ECHO behind
that distracts same-color guards for two phases.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import pyxel

# ── Config ──
SCREEN_W = 256
SCREEN_H = 256
TILE_SIZE = 16
GRID_W = SCREEN_W // TILE_SIZE  # 16
GRID_H = SCREEN_H // TILE_SIZE  # 16
DISPLAY_SCALE = 3
FPS = 30

# Raw color ints — avoids TYPE_CHECKING pyxel import issues
COLOR_BLACK = 0
COLOR_NAVY = 1
COLOR_PURPLE = 2
COLOR_GREEN = 3
COLOR_BROWN = 4
COLOR_DARK_BLUE = 5
COLOR_LIGHT_BLUE = 6
COLOR_WHITE = 7
COLOR_RED = 8
COLOR_ORANGE = 9
COLOR_YELLOW = 10
COLOR_LIME = 11
COLOR_CYAN = 12
COLOR_GRAY = 13
COLOR_PINK = 14
COLOR_PEACH = 15

# Guard color palette — indices + names (English-only for Pyxel BDF font)
GUARD_COLORS: tuple[int, ...] = (COLOR_RED, COLOR_GREEN, COLOR_LIGHT_BLUE, COLOR_YELLOW)
GUARD_NAMES: tuple[str, ...] = ("RED", "GRN", "BLU", "YEL")
NUM_COLORS = len(GUARD_COLORS)

PHASE_DURATION = 90   # frames per color phase (~3 sec at 30 FPS)
PLAYER_HP = 3
GUARD_COUNT = 5
GEM_COUNT = 8
WALL_COUNT = 14
TIME_LIMIT = 60 * FPS
VISION_RANGE = 3       # tiles
ECHO_LIFE = PHASE_DURATION * 2
CAUGHT_INVULN = 30     # frames of invulnerability after catch
GEM_SCORE = 50
TIME_SCORE_MULT = 10

# ── Enums ──
class Direction(IntEnum):
    DOWN = 0
    LEFT = 1
    UP = 2
    RIGHT = 3


DIR_VECTORS: dict[Direction, tuple[int, int]] = {
    Direction.DOWN: (0, 1),
    Direction.LEFT: (-1, 0),
    Direction.UP: (0, -1),
    Direction.RIGHT: (1, 0),
}


class Phase(IntEnum):
    PLAYING = 0
    CAUGHT = 1
    VICTORY = 2
    DEFEAT = 3


# ── Data Classes ──
@dataclass
class Guard:
    x: int
    y: int
    color: int  # index into GUARD_COLORS
    direction: Direction
    patrol_min_x: int
    patrol_min_y: int
    patrol_max_x: int
    patrol_max_y: int
    distracted: bool = False
    echo_gx: int = 0
    echo_gy: int = 0


@dataclass
class Echo:
    gx: int  # grid x
    gy: int  # grid y
    color: int  # index into GUARD_COLORS
    life: int


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


# ── Game ──
class Game:
    """Top-down grid stealth: evade guards, reach exit, build echoes."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ECHO STEALTH", fps=FPS, display_scale=DISPLAY_SCALE)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.PLAYING
        self.player_gx = 1
        self.player_gy = 1
        self.player_hp = PLAYER_HP
        self.score = 0
        self.max_score = 0
        self.gems_collected = 0
        self.active_color = 0
        self.phase_timer = PHASE_DURATION
        self.game_timer = TIME_LIMIT
        self.caught_timer = 0
        self.caught_flash = 0

        # Grid: 0=empty, 1=wall
        self.grid: list[list[int]] = [[0] * GRID_W for _ in range(GRID_H)]
        self.guards: list[Guard] = []
        self.echoes: list[Echo] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.gems: list[tuple[int, int, int]] = []  # (gx, gy, color_index)
        self.exit_gx = GRID_W - 2
        self.exit_gy = GRID_H - 2

        self._generate_level()

    # ── Level Generation ──

    def _generate_level(self) -> None:
        # Phase 1: Place guards first, mark their patrol paths as reserved
        reserved: set[tuple[int, int]] = {(1, 1), (self.exit_gx, self.exit_gy)}
        patrol_paths: list[list[tuple[int, int]]] = []

        for i in range(GUARD_COUNT):
            color = i % NUM_COLORS
            for _ in range(100):
                path: list[tuple[int, int]] = []
                if self._rng.random() < 0.5:
                    # horizontal patrol
                    gy = self._rng.randint(2, GRID_H - 3)
                    gx1 = self._rng.randint(1, GRID_W // 3)
                    gx2 = self._rng.randint(2 * GRID_W // 3, GRID_W - 2)
                    for px in range(min(gx1, gx2), max(gx1, gx2) + 1):
                        path.append((px, gy))
                else:
                    # vertical patrol
                    gx = self._rng.randint(2, GRID_W - 3)
                    gy1 = self._rng.randint(1, GRID_H // 3)
                    gy2 = self._rng.randint(2 * GRID_H // 3, GRID_H - 2)
                    for py in range(min(gy1, gy2), max(gy1, gy2) + 1):
                        path.append((gx, py))
                # Check path doesn't overlap existing reserved
                if any(p in reserved for p in path):
                    continue
                for p in path:
                    reserved.add(p)
                patrol_paths.append(path)
                # Create Guard at the start of the path
                sx, sy = path[0]
                if abs(path[-1][0] - sx) > abs(path[-1][1] - sy):
                    # Horizontal
                    g = Guard(
                        x=sx, y=sy, color=color,
                        direction=Direction.RIGHT if path[-1][0] > sx else Direction.LEFT,
                        patrol_min_x=min(sx, path[-1][0]), patrol_min_y=sy,
                        patrol_max_x=max(sx, path[-1][0]), patrol_max_y=sy,
                    )
                else:
                    # Vertical
                    g = Guard(
                        x=sx, y=sy, color=color,
                        direction=Direction.DOWN if path[-1][1] > sy else Direction.UP,
                        patrol_min_x=sx, patrol_min_y=min(sy, path[-1][1]),
                        patrol_max_x=sx, patrol_max_y=max(sy, path[-1][1]),
                    )
                self.guards.append(g)
                break

        # Phase 2: Place walls in remaining free tiles
        free_tiles = [
            (x, y)
            for y in range(1, GRID_H - 1)
            for x in range(1, GRID_W - 1)
            if (x, y) not in reserved
        ]
        self._rng.shuffle(free_tiles)
        for wx, wy in free_tiles[:WALL_COUNT]:
            self.grid[wy][wx] = 1

        # Phase 3: Place gems in remaining free non-wall tiles
        gem_candidates = [
            (x, y) for (x, y) in free_tiles[WALL_COUNT:]
            if (x, y) not in reserved
        ]
        self._rng.shuffle(gem_candidates)
        for i in range(min(GEM_COUNT, len(gem_candidates))):
            gx, gy = gem_candidates[i]
            gcolor = self._rng.randint(0, NUM_COLORS - 1)
            self.gems.append((gx, gy, gcolor))

    # ── Update ──

    def update(self) -> None:
        if self.phase == Phase.DEFEAT or self.phase == Phase.VICTORY:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        if self.phase == Phase.CAUGHT:
            self._update_caught()
            return

        # Phase timer
        self.phase_timer -= 1
        if self.phase_timer <= 0:
            self.active_color = (self.active_color + 1) % NUM_COLORS
            self.phase_timer = PHASE_DURATION

        # Game timer
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.DEFEAT
            return

        # Player movement
        dx, dy = 0, 0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -1
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = 1
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -1
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = 1
        if dx != 0 or dy != 0:
            nx = self.player_gx + dx
            ny = self.player_gy + dy
            if self._walkable(nx, ny):
                self.player_gx = nx
                self.player_gy = ny

        self._update_guards()
        self._update_echoes()
        self._update_particles()
        self._update_floating_texts()
        self._collect_gems()
        self._check_detection()
        self._check_exit()

    def _walkable(self, gx: int, gy: int) -> bool:
        if gx < 0 or gx >= GRID_W or gy < 0 or gy >= GRID_H:
            return False
        return self.grid[gy][gx] == 0

    def _update_guards(self) -> None:
        for g in self.guards:
            # Echo distraction: same-color guard moves toward nearest echo
            g.distracted = False
            nearest_echo: Echo | None = None
            nearest_dist = 999
            for e in self.echoes:
                if e.color == g.color and e.life > 0:
                    d = abs(e.gx - g.x) + abs(e.gy - g.y)
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest_echo = e
            if nearest_echo is not None and nearest_dist > 0:
                g.distracted = True
                g.echo_gx = nearest_echo.gx
                g.echo_gy = nearest_echo.gy
                # Move toward echo
                if abs(g.x - nearest_echo.gx) >= abs(g.y - nearest_echo.gy):
                    step_x = 1 if nearest_echo.gx > g.x else -1
                    step_y = 0
                else:
                    step_x = 0
                    step_y = 1 if nearest_echo.gy > g.y else -1
                nx = g.x + step_x
                ny = g.y + step_y
                # Clamp to patrol bounds
                nx = max(g.patrol_min_x, min(g.patrol_max_x, nx))
                ny = max(g.patrol_min_y, min(g.patrol_max_y, ny))
                g.x = nx
                g.y = ny
                # Update facing
                if step_x > 0:
                    g.direction = Direction.RIGHT
                elif step_x < 0:
                    g.direction = Direction.LEFT
                elif step_y > 0:
                    g.direction = Direction.DOWN
                elif step_y < 0:
                    g.direction = Direction.UP
            else:
                # Normal patrol movement
                dx, dy = DIR_VECTORS[g.direction]
                nx = g.x + dx
                ny = g.y + dy
                if nx < g.patrol_min_x or nx > g.patrol_max_x or ny < g.patrol_min_y or ny > g.patrol_max_y:
                    # Reverse
                    g.direction = Direction((int(g.direction) + 2) % 4)
                    dx, dy = DIR_VECTORS[g.direction]
                    nx = g.x + dx
                    ny = g.y + dy
                g.x = nx
                g.y = ny

    def _update_echoes(self) -> None:
        for e in self.echoes:
            e.life -= 1
        self.echoes = [e for e in self.echoes if e.life > 0]

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _collect_gems(self) -> None:
        collected: list[int] = []
        for i, (gx, gy, gcolor) in enumerate(self.gems):
            if self.player_gx == gx and self.player_gy == gy:
                collected.append(i)
                self.gems_collected += 1
                pts = GEM_SCORE * (1 + (gcolor == self.active_color))
                self.score += int(pts)
                self._spawn_particles(gx, gy, GUARD_COLORS[gcolor], 8)
                self._spawn_floating_text(gx, gy, f"+{int(pts)}", GUARD_COLORS[gcolor])
        for i in reversed(collected):
            self.gems.pop(i)

    def _check_detection(self) -> None:
        if self.caught_timer > 0:
            return  # invulnerable
        for g in self.guards:
            if g.color != self.active_color:
                continue  # inactive guards can't see
            if self._in_vision(g):
                self._on_caught(g)
                return

    def _in_vision(self, guard: Guard) -> bool:
        """Check if player is in guard's vision cone."""
        dx = self.player_gx - guard.x
        dy = self.player_gy - guard.y
        gdx, gdy = DIR_VECTORS[guard.direction]
        forward = gdx * dx + gdy * dy
        if forward <= 0:
            return False
        if forward > VISION_RANGE:
            return False
        # lateral distance (perpendicular)
        lateral = abs(-gdy * dx + gdx * dy)
        # Allow vision widening: lateral <= forward * 0.6 + 0.5
        if lateral > forward * 0.6 + 0.5:
            return False
        # Wall occlusion: check tiles along line
        return self._line_of_sight(guard.x, guard.y, self.player_gx, self.player_gy)

    def _line_of_sight(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        """Bresenham line check — returns False if a wall blocks the view."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        cx, cy = x0, y0
        first = True
        while True:
            if not first and not (cx == x1 and cy == y1):
                if not self._walkable(cx, cy):
                    return False
            if cx == x1 and cy == y1:
                break
            first = False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy
        return True

    def _on_caught(self, guard: Guard) -> None:
        self.player_hp -= 1
        self.phase = Phase.CAUGHT
        self.caught_timer = CAUGHT_INVULN
        self.caught_flash = 0
        # Leave echo
        self.echoes.append(Echo(gx=guard.x, gy=guard.y, color=guard.color, life=ECHO_LIFE))
        self._spawn_particles(self.player_gx, self.player_gy, COLOR_WHITE, 12)
        self._spawn_floating_text(self.player_gx, self.player_gy, "CAUGHT!", COLOR_RED)
        if self.player_hp <= 0:
            self.phase = Phase.DEFEAT

    def _update_caught(self) -> None:
        self.caught_timer -= 1
        self.caught_flash += 1
        self._update_particles()
        self._update_floating_texts()
        self._update_echoes()
        if self.caught_timer <= 0:
            if self.player_hp > 0:
                self.phase = Phase.PLAYING
                # Respawn at start
                self.player_gx = 1
                self.player_gy = 1
                self.caught_timer = 0

    def _check_exit(self) -> None:
        if self.player_gx == self.exit_gx and self.player_gy == self.exit_gy:
            time_bonus = self.game_timer // FPS * TIME_SCORE_MULT
            self.score += time_bonus
            self.phase = Phase.VICTORY
            self._spawn_particles(self.exit_gx, self.exit_gy, COLOR_GREEN, 30)
            self._spawn_floating_text(self.exit_gx, self.exit_gy, f"+{time_bonus}", COLOR_LIME)
            if self.score > self.max_score:
                self.max_score = self.score

    # ── Particle Helpers ──

    def _spawn_particles(self, gx: int, gy: int, color: int, count: int) -> None:
        cx = gx * TILE_SIZE + TILE_SIZE // 2
        cy = gy * TILE_SIZE + TILE_SIZE // 2
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.random() * 2.0 + 0.5
            life = self._rng.randint(8, 20)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life, color=color,
            ))

    def _spawn_floating_text(self, gx: int, gy: int, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=gx * TILE_SIZE + TILE_SIZE // 2 - len(text) * 2,
            y=gy * TILE_SIZE - 4,
            text=text, life=25, color=color,
        ))

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        # Grid background
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                px = gx * TILE_SIZE
                py = gy * TILE_SIZE
                if self.grid[gy][gx] == 1:
                    pyxel.rect(px, py, TILE_SIZE, TILE_SIZE, COLOR_GRAY)
                else:
                    # Floor with subtle checker
                    c = COLOR_NAVY if (gx + gy) % 2 == 0 else COLOR_DARK_BLUE
                    pyxel.rect(px, py, TILE_SIZE, TILE_SIZE, c)

        # Exit
        ex = self.exit_gx * TILE_SIZE
        ey = self.exit_gy * TILE_SIZE
        pyxel.rect(ex + 2, ey + 2, TILE_SIZE - 4, TILE_SIZE - 4, COLOR_GREEN)
        pyxel.text(ex + 4, ey + 5, "EX", COLOR_BLACK)

        # Gems
        for gx, gy, gcolor in self.gems:
            px = gx * TILE_SIZE + 4
            py = gy * TILE_SIZE + 4
            pyxel.circ(px + 4, py + 4, 3, GUARD_COLORS[gcolor])

        # Echoes
        for e in self.echoes:
            alpha = e.life / ECHO_LIFE
            px = e.gx * TILE_SIZE
            py = e.gy * TILE_SIZE
            col = GUARD_COLORS[e.color]
            # Pulsing ghost square
            radius = int(6 * alpha)
            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2
            if radius > 0:
                pyxel.circb(cx, cy, radius, col)

        # Guards
        for g in self.guards:
            px = g.x * TILE_SIZE
            py = g.y * TILE_SIZE
            active = g.color == self.active_color
            body_col = GUARD_COLORS[g.color]
            if g.distracted:
                # Draw line toward echo
                ex2 = g.echo_gx * TILE_SIZE + TILE_SIZE // 2
                ey2 = g.echo_gy * TILE_SIZE + TILE_SIZE // 2
                pyxel.line(px + TILE_SIZE // 2, py + TILE_SIZE // 2, ex2, ey2, body_col)
            # Body
            pyxel.rect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4, body_col)
            # Eye / direction indicator
            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2
            edx, edy = DIR_VECTORS[g.direction]
            pyxel.rect(cx + edx * 3 - 1, cy + edy * 3 - 1, 3, 3, COLOR_WHITE)
            # Vision cone (only active color)
            if active:
                self._draw_vision_cone(g)

        # Player
        if self.phase != Phase.CAUGHT or self.caught_flash % 6 < 3:
            px = self.player_gx * TILE_SIZE
            py = self.player_gy * TILE_SIZE
            pyxel.rect(px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6, COLOR_CYAN)
            # Eyes
            pyxel.rect(px + 5, py + 5, 2, 2, COLOR_WHITE)
            pyxel.rect(px + 9, py + 5, 2, 2, COLOR_WHITE)

        # Particles
        for p in self.particles:
            alpha = p.life / 20
            col = p.color if alpha > 0.3 else COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), col)

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        # HUD
        self._draw_hud()

    def _draw_vision_cone(self, guard: Guard) -> None:
        """Draw vision cone tiles for an active guard."""
        gdx, gdy = DIR_VECTORS[guard.direction]
        for d in range(1, VISION_RANGE + 1):
            fx = guard.x + gdx * d
            fy = guard.y + gdy * d
            if not (0 <= fx < GRID_W and 0 <= fy < GRID_H):
                break
            # Lateral spread
            for lat in range(-d, d + 1):
                if gdx != 0:  # horizontal facing
                    tx = fx
                    ty = fy + lat
                else:  # vertical facing
                    tx = fx + lat
                    ty = fy
                if 0 <= tx < GRID_W and 0 <= ty < GRID_H:
                    if self.grid[ty][tx] == 1:
                        continue  # wall blocks vision
                    px = tx * TILE_SIZE
                    py = ty * TILE_SIZE
                    # Semi-transparent overlay
                    alpha = 1.0 - d / (VISION_RANGE + 1)
                    if alpha > 0.4:
                        col = GUARD_COLORS[guard.color]
                        pyxel.rect(px + 1, py + 1, TILE_SIZE - 2, TILE_SIZE - 2, col)

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 8, COLOR_BLACK)
        # Active color indicator
        active_col = GUARD_COLORS[self.active_color]
        active_name = GUARD_NAMES[self.active_color]
        pyxel.rect(1, 1, 6, 6, active_col)
        pyxel.text(9, 0, f"ACTIVE:{active_name}", COLOR_WHITE)
        # Phase timer bar
        bar_w = 40
        frac = self.phase_timer / PHASE_DURATION
        pyxel.rect(SCREEN_W - 42, 1, bar_w, 6, COLOR_GRAY)
        pyxel.rect(SCREEN_W - 42, 1, int(bar_w * frac), 6, active_col)
        # HP
        hp_str = "HP:" + "I" * self.player_hp
        pyxel.text(SCREEN_W - 90, 0, hp_str, COLOR_RED)

        # Bottom bar
        pyxel.rect(0, SCREEN_H - 10, SCREEN_W, 10, COLOR_BLACK)
        time_sec = self.game_timer // FPS
        pyxel.text(1, SCREEN_H - 9, f"TIME:{time_sec:02d}", COLOR_WHITE)
        pyxel.text(70, SCREEN_H - 9, f"SCORE:{self.score}", COLOR_YELLOW)
        pyxel.text(150, SCREEN_H - 9, f"GEMS:{self.gems_collected}", COLOR_CYAN)
        # Exit hint
        pyxel.text(SCREEN_W - 40, SCREEN_H - 9, "[R]ESTART", COLOR_GRAY)

        # Victory / Defeat overlay
        if self.phase == Phase.VICTORY:
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 4, "ESCAPED!", COLOR_GREEN)
            pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 4, f"SCORE: {self.score}", COLOR_YELLOW)
        elif self.phase == Phase.DEFEAT:
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 4, "CAUGHT!", COLOR_RED)
            pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 4, f"SCORE: {self.score}", COLOR_YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
