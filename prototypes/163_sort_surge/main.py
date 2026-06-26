"""163_sort_surge — Color-Match Conveyor Belt Sorter."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Phase Enum ──


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Data Classes ──


@dataclass
class Package:
    x: float
    y: float
    color: int
    sorted: bool = False
    speed: float = 0.5


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: int
    life: int
    vy: float = -0.6


# ── Constants ──

SCREEN_W = 320
SCREEN_H = 240

# Colors
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

PACKAGE_COLORS = (RED, GREEN, DARK_BLUE, YELLOW, PINK)
COLOR_NAMES: dict[int, str] = {
    RED: "RED",
    GREEN: "GRN",
    DARK_BLUE: "BLU",
    YELLOW: "YLW",
    PINK: "PNK",
}

# Conveyor lanes (y positions)
LANE_Y = (30, 60, 90, 120, 150)
LANE_COLOR = (DARK_BLUE, LIGHT_BLUE, DARK_BLUE, LIGHT_BLUE, DARK_BLUE)

# Bin positions
BIN_Y = 200
BIN_HEIGHT = 28
BIN_W = 58
BIN_GAP = 2
BIN_TOTAL = BIN_W + BIN_GAP
BINS_X_START = (SCREEN_W - (BIN_W * 5 + BIN_GAP * 4)) // 2  # center the bins

# HUD
HUD_Y = 10
OVERFLOW_BAR_X = SCREEN_W - 90
OVERFLOW_BAR_Y = 4
OVERFLOW_BAR_W = 80
OVERFLOW_BAR_H = 8

# Package
MAX_PACKAGES = 10
PACKAGE_R = 8
PACKAGE_END_X = 8.0

# Gameplay
OVERFLOW_MAX = 100.0
OVERFLOW_WRONG_SORT = 20.0
OVERFLOW_MISS = 30.0
OVERFLOW_DECAY = 0.01
COMBO_SURGE_THRESHOLD = 5
SURGE_DURATION = 5.0  # seconds
SURGE_SCORE_MULT = 3
BASE_SCORE = 10
SPAWN_INTERVAL_INITIAL = 2.0  # seconds
SPAWN_INTERVAL_MIN = 0.5
SPAWN_INTERVAL_DECAY = 0.01  # per second of gameplay
PACKAGE_SPEED_INITIAL = 0.5  # px per frame
PACKAGE_SPEED_MAX = 2.0
PACKAGE_SPEED_INCREASE = 0.002  # per second of gameplay

# Particles
SORT_PARTICLES = 8
SURGE_PARTICLES = 20
MISTAKE_PARTICLES = 4

# ── Game Class ──


class Game:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self.packages: list[Package] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.overflow: float = 0.0
        self.surge_timer: float = 0.0
        self.phase: Phase = Phase.TITLE
        self.spawn_timer: float = 0.0
        self.game_timer: float = 0.0
        self._last_sort_color: int | None = None
        self._auto_sort_timer: float = 0.0
        self._selected_bin_color: int = RED

    def reset(self) -> None:
        self.packages.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.overflow = 0.0
        self.surge_timer = 0.0
        self.phase = Phase.TITLE
        self.spawn_timer = 0.0
        self.game_timer = 0.0
        self._last_sort_color = None
        self._auto_sort_timer = 0.0
        self._selected_bin_color = RED

    def start_game(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING

    # ── Difficulty Scaling ──

    def _difficulty_params(self) -> tuple[float, float]:
        spawn_interval = max(
            SPAWN_INTERVAL_MIN,
            SPAWN_INTERVAL_INITIAL - SPAWN_INTERVAL_DECAY * self.game_timer,
        )
        speed = min(
            PACKAGE_SPEED_MAX,
            PACKAGE_SPEED_INITIAL + PACKAGE_SPEED_INCREASE * self.game_timer,
        )
        return spawn_interval, speed

    # ── Spawning ──

    def _spawn_package(self) -> None:
        if len(self.packages) >= MAX_PACKAGES:
            return
        lane = self._rng.randint(0, 4)
        color = self._rng.choice(PACKAGE_COLORS)
        _, speed = self._difficulty_params()
        self.packages.append(
            Package(x=float(SCREEN_W - 16), y=float(LANE_Y[lane]), color=color, speed=speed)
        )

    # ── Updating ──

    def _update_packages(self) -> None:
        remaining: list[Package] = []
        for pkg in self.packages:
            if pkg.sorted:
                continue
            pkg.x -= pkg.speed
            if pkg.x <= PACKAGE_END_X:
                self.overflow += OVERFLOW_MISS
                self._spawn_particles(pkg.x, pkg.y, RED, MISTAKE_PARTICLES)
                self._add_floating_text("MISS!", pkg.x, pkg.y, RED)
            else:
                remaining.append(pkg)
        self.packages = remaining
        if self.overflow > OVERFLOW_MAX:
            self.overflow = OVERFLOW_MAX

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    def _update_surge(self, dt: float) -> None:
        if self.surge_timer <= 0:
            return
        self.surge_timer -= dt
        if self.surge_timer <= 0:
            self.surge_timer = 0.0
            return
        self._auto_sort_timer -= dt
        if self._auto_sort_timer <= 0:
            self._auto_sort_timer = 1.0
            for pkg in self.packages:
                if not pkg.sorted:
                    self.combo += 1
                    self._last_sort_color = pkg.color
                    points = BASE_SCORE * self.combo * SURGE_SCORE_MULT
                    self.score += points
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    pkg.sorted = True
                    self._spawn_particles(pkg.x, pkg.y, WHITE, SORT_PARTICLES)
                    self._add_floating_text(f"+{points}", pkg.x, pkg.y, WHITE)
                    break

    def update(self, dt: float = 1.0 / 30.0) -> None:
        if self.phase != Phase.PLAYING:
            return

        # Game over check (before decay, to catch exactly-at-max)
        if self.overflow >= OVERFLOW_MAX:
            self.phase = Phase.GAME_OVER
            return

        self.game_timer += dt

        # Overflow decay
        self.overflow = max(0.0, self.overflow - OVERFLOW_DECAY)

        # Spawn
        spawn_interval, _ = self._difficulty_params()
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = spawn_interval
            self._spawn_package()

        # Surge
        self._update_surge(dt)

        # Move packages
        self._update_packages()

        # Effects
        self._update_particles()
        self._update_floating_texts()

        # Game over check (after packages move too)
        if self.overflow >= OVERFLOW_MAX:
            self.phase = Phase.GAME_OVER

    # ── Sorting ──

    def _sort_package(self, idx: int) -> bool:
        if idx < 0 or idx >= len(self.packages):
            return False
        pkg = self.packages[idx]
        if pkg.sorted:
            return False

        # SURGE mode: any color matches
        if self.surge_timer > 0:
            self.combo += 1
            self._last_sort_color = pkg.color
            points = BASE_SCORE * self.combo * SURGE_SCORE_MULT
            self.score += points
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            pkg.sorted = True
            self._spawn_particles(pkg.x, pkg.y, WHITE, SORT_PARTICLES)
            self._add_floating_text(f"+{points}", pkg.x, pkg.y, WHITE)
            return True

        if pkg.color == self._selected_bin_color:
            # Correct sort
            if self._last_sort_color == pkg.color:
                self.combo += 1
            else:
                self.combo = 1
            self._last_sort_color = pkg.color
            points = BASE_SCORE * self.combo
            self.score += points
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            pkg.sorted = True
            self._spawn_particles(pkg.x, pkg.y, pkg.color, SORT_PARTICLES)
            self._add_floating_text(f"+{points}", pkg.x, pkg.y, WHITE)

            # Check SURGE activation
            if self.combo >= COMBO_SURGE_THRESHOLD:
                self._activate_surge()

            return True
        else:
            # Wrong sort
            self.combo = 0
            self._last_sort_color = None
            self.overflow += OVERFLOW_WRONG_SORT
            self._spawn_particles(pkg.x, pkg.y, RED, MISTAKE_PARTICLES)
            self._add_floating_text("WRONG!", pkg.x, pkg.y, ORANGE)
            return False

    def _activate_surge(self) -> None:
        self.surge_timer = SURGE_DURATION
        self._auto_sort_timer = 0.0
        self._spawn_particles(SCREEN_W / 2, SCREEN_H / 2, WHITE, SURGE_PARTICLES)
        self._add_floating_text("SURGE!", SCREEN_W / 2 - 15, 120, YELLOW)

    # ── Effects ──

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            spd = self._rng.uniform(0.4, 1.8)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd - 0.5,
                    color=color,
                    life=self._rng.randint(12, 22),
                )
            )

    def _add_floating_text(self, text: str, x: float, y: float, color: int) -> None:
        self.floating_texts.append(FloatingText(text=text, x=x, y=y, color=color, life=30))

    # ── Mouse input helpers (called from App, not testable methods) ──

    def select_bin(self, bin_index: int) -> None:
        if 0 <= bin_index < 5:
            self._selected_bin_color = PACKAGE_COLORS[bin_index]

    def click_package(self, mx: float, my: float) -> bool:
        closest_idx = -1
        closest_dist = float("inf")
        for i, pkg in enumerate(self.packages):
            if pkg.sorted:
                continue
            dist = math.hypot(mx - pkg.x, my - pkg.y)
            if dist < PACKAGE_R + 4 and dist < closest_dist:
                closest_dist = dist
                closest_idx = i
        if closest_idx >= 0:
            return self._sort_package(closest_idx)
        return False

    def click_bin(self, mx: float, my: float) -> int:
        if my < BIN_Y or my > BIN_Y + BIN_HEIGHT:
            return -1
        if mx < BINS_X_START or mx > BINS_X_START + BIN_TOTAL * 4 + BIN_W:
            return -1
        idx = int((mx - BINS_X_START) / BIN_TOTAL)
        if 0 <= idx < 5:
            self.select_bin(idx)
            return idx
        return -1


# ── Draw Helpers ──


def _bin_x(idx: int) -> int:
    return BINS_X_START + idx * BIN_TOTAL


def draw_title(g: Game) -> None:
    pyxel.cls(NAVY)
    pyxel.text(128, 40, "SORT SURGE", WHITE)
    pyxel.text(60, 70, "Click packages to sort into matching bins", GRAY)
    pyxel.text(50, 90, "Same color = COMBO!  COMBO>=5 = SURGE!", LIME)
    pyxel.text(65, 120, "SURGE: auto-sort + 3x score", CYAN)
    pyxel.text(50, 150, "Wrong sort or missed pkg = OVERFLOW", ORANGE)
    pyxel.text(85, 180, "OVERFLOW 100 = GAME OVER", RED)
    if pyxel.frame_count % 40 < 25:
        pyxel.text(80, 215, "Press SPACE to start", WHITE)


def draw_game(g: Game) -> None:
    pyxel.cls(DARK_BLUE)

    # Conveyor belts
    for yi, y in enumerate(LANE_Y):
        lc = LANE_COLOR[yi]
        pyxel.line(0, y, SCREEN_W, y, lc)
        # Arrow indicators
        anim_offset = (pyxel.frame_count * 2) % 16
        for ax in range(0, SCREEN_W, 16):
            dx = ax + anim_offset % 16
            pyxel.line(dx, y - 1, dx + 4, y, lc)
            pyxel.line(dx + 4, y, dx, y + 1, lc)

    # Packages
    for pkg in g.packages:
        if pkg.sorted:
            continue
        x = int(pkg.x)
        y = int(pkg.y)
        pyxel.circ(x, y, PACKAGE_R, pkg.color)
        pyxel.circb(x, y, PACKAGE_R, WHITE)
        # Package shape: small square inside
        pyxel.rect(x - 3, y - 3, 6, 6, WHITE)

    # Sort bins at bottom
    for i, c in enumerate(PACKAGE_COLORS):
        bx = _bin_x(i)
        pyxel.rect(bx, BIN_Y, BIN_W, BIN_HEIGHT, c)
        if c == g._selected_bin_color:
            pyxel.rectb(bx - 1, BIN_Y - 1, BIN_W + 2, BIN_HEIGHT + 2, WHITE)
        else:
            pyxel.rectb(bx, BIN_Y, BIN_W, BIN_HEIGHT, GRAY)
        # Color name label
        label = COLOR_NAMES.get(c, "???")
        pyxel.text(bx + 14, BIN_Y + BIN_HEIGHT + 2, label, c)

    # HUD
    pyxel.text(4, HUD_Y, f"SCORE {g.score}", WHITE)
    pyxel.text(4, HUD_Y + 10, f"COMBO x{g.combo}", YELLOW)

    # Overflow bar
    pyxel.rectb(OVERFLOW_BAR_X - 1, OVERFLOW_BAR_Y - 1, OVERFLOW_BAR_W + 2, OVERFLOW_BAR_H + 2, GRAY)
    o_ratio = g.overflow / OVERFLOW_MAX
    o_w = int(OVERFLOW_BAR_W * o_ratio)
    if g.overflow < 40:
        oc = GREEN
    elif g.overflow < 70:
        oc = YELLOW
    else:
        oc = RED
    pyxel.rect(OVERFLOW_BAR_X, OVERFLOW_BAR_Y, o_w, OVERFLOW_BAR_H, oc)
    pyxel.text(OVERFLOW_BAR_X, OVERFLOW_BAR_Y + 10, f"OVF {int(g.overflow)}%", WHITE)

    # SURGE indicator
    if g.surge_timer > 0:
        sr = g.surge_timer / SURGE_DURATION
        sdw = int(60 * sr)
        rc = PACKAGE_COLORS[(pyxel.frame_count // 5) % 5]
        pyxel.text(SCREEN_W // 2 - 20, HUD_Y, "SURGE!", rc)
        pyxel.rect(SCREEN_W // 2 - 30, HUD_Y + 10, 60, 4, GRAY)
        pyxel.rect(SCREEN_W // 2 - 30, HUD_Y + 10, sdw, 4, WHITE)

    # Particles
    for p in g.particles:
        alpha = min(p.life, 8)
        if alpha > 0:
            pyxel.pset(int(p.x), int(p.y), p.color)

    # Floating texts
    for ft in g.floating_texts:
        alpha = min(ft.life, 15)
        if alpha > 0:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)


def draw_game_over(g: Game) -> None:
    pyxel.cls(BLACK)
    pyxel.rect(50, 30, 220, 180, NAVY)
    pyxel.rectb(50, 30, 220, 180, WHITE)
    pyxel.text(115, 42, "GAME OVER", RED)
    pyxel.text(80, 72, f"SCORE:      {g.score}", WHITE)
    pyxel.text(80, 92, f"MAX COMBO:  x{g.max_combo}", YELLOW)
    pyxel.text(80, 112, f"TIME:       {int(g.game_timer)}s", GRAY)
    last_str = COLOR_NAMES[g._last_sort_color] if g._last_sort_color is not None else "-"
    pyxel.text(80, 140, f"LAST COLOR:  {last_str}", GRAY)
    if pyxel.frame_count % 40 < 25:
        pyxel.text(74, 185, "Press SPACE to retry", WHITE)


# ── Pyxel App ──


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Sort Surge", display_scale=2)
        pyxel.mouse(True)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.start_game()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                # Try clicking a bin first
                bin_idx = g.click_bin(float(mx), float(my))
                if bin_idx < 0:
                    # Not a bin click — try package
                    g.click_package(float(mx), float(my))
            g.update()
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.start_game()

    def draw(self) -> None:
        g = self.game
        if g.phase == Phase.TITLE:
            draw_title(g)
        elif g.phase == Phase.PLAYING:
            draw_game(g)
        elif g.phase == Phase.GAME_OVER:
            draw_game_over(g)


def main() -> None:
    App()


if __name__ == "__main__":
    main()
