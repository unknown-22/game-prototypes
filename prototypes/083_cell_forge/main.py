from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_COLS = 16
GRID_ROWS = 12
CELL_SIZE = 15
CELL_GAP = 1
CELL_STEP = CELL_SIZE + CELL_GAP
GRID_OFFSET_X = (320 - GRID_COLS * CELL_STEP + CELL_GAP) // 2
GRID_OFFSET_Y = 6
HUD_Y = 216
HUD_HEIGHT = 24
MAX_TIER = 4
SYNTHESIS_THRESHOLD = 3
OVERPOP_THRESHOLD = 7
HEAT_LIMIT = 5
MAX_ENERGY = 20
INITIAL_ENERGY = 8
EVOLVE_DELAY = 15
SYNTH_DELAY = 30

# Pyxel colour constants
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


class Phase(Enum):
    TITLE = auto()
    SEED = auto()
    EVOLVING = auto()
    SYNTHESIS = auto()
    GAME_OVER = auto()


class CellColor(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
    YELLOW = 3


_TIER_COLOR_MAP: dict[tuple[CellColor, int], int] = {
    (CellColor.RED, 1): RED,
    (CellColor.RED, 2): ORANGE,
    (CellColor.RED, 3): YELLOW,
    (CellColor.RED, 4): WHITE,
    (CellColor.GREEN, 1): GREEN,
    (CellColor.GREEN, 2): LIME,
    (CellColor.GREEN, 3): CYAN,
    (CellColor.GREEN, 4): WHITE,
    (CellColor.BLUE, 1): LIGHT_BLUE,
    (CellColor.BLUE, 2): CYAN,
    (CellColor.BLUE, 3): PURPLE,
    (CellColor.BLUE, 4): WHITE,
    (CellColor.YELLOW, 1): YELLOW,
    (CellColor.YELLOW, 2): ORANGE,
    (CellColor.YELLOW, 3): PINK,
    (CellColor.YELLOW, 4): WHITE,
}

_NEIGHBOUR_OFFSETS = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Cell:
    alive: bool = False
    color: CellColor | None = None
    tier: int = 1


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: float


@dataclass
class SynthesisEvent:
    cx: int
    cy: int
    color: CellColor
    new_tier: int
    cluster_size: int
    timer: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tier_color(color: CellColor, tier: int) -> int:
    t = min(tier, MAX_TIER)
    return _TIER_COLOR_MAP.get((color, t), WHITE)


def cell_to_pixel(col: int, row: int) -> tuple[int, int]:
    x = GRID_OFFSET_X + col * CELL_STEP
    y = GRID_OFFSET_Y + row * CELL_STEP
    return x, y


def pixel_to_cell(px: int, py: int) -> tuple[int, int] | None:
    if px < GRID_OFFSET_X or py < GRID_OFFSET_Y:
        return None
    col = (px - GRID_OFFSET_X) // CELL_STEP
    row = (py - GRID_OFFSET_Y) // CELL_STEP
    if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
        local_x = (px - GRID_OFFSET_X) % CELL_STEP
        local_y = (py - GRID_OFFSET_Y) % CELL_STEP
        if local_x < CELL_SIZE and local_y < CELL_SIZE:
            return col, row
    return None


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[Cell]] = []
        self.score: int = 0
        self.generation: int = 0
        self.energy: int = INITIAL_ENERGY
        self.heat: int = 0
        self.max_tier: int = 1
        self.combo: int = 0
        self.max_combo: int = 0
        self.synthesis_events: list[SynthesisEvent] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.mouse_cx: int = -1
        self.mouse_cy: int = -1
        self._evolve_timer: int = 0
        self._synth_timer: int = 0
        self._rng: random.Random = random.Random()
        self._game_over_timer: int = 0
        self._init_grid()

    def _init_grid(self) -> None:
        self.grid = [
            [Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]

    def reset(self) -> None:
        self._init_state()

    # ------------------------------------------------------------------
    # Grid helpers
    # ------------------------------------------------------------------

    def _in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS

    def _count_neighbors(
        self, col: int, row: int
    ) -> tuple[int, CellColor | None]:
        live_count = 0
        color_counts: dict[CellColor, int] = {}
        for dc, dr in _NEIGHBOUR_OFFSETS:
            nc, nr = col + dc, row + dr
            if self._in_bounds(nc, nr):
                cell = self.grid[nr][nc]
                if cell.alive and cell.color is not None:
                    live_count += 1
                    color_counts[cell.color] = (
                        color_counts.get(cell.color, 0) + 1
                    )
        if live_count == 0:
            return 0, None
        majority = max(color_counts, key=lambda c: color_counts[c])
        return live_count, majority

    # ------------------------------------------------------------------
    # Seed placement
    # ------------------------------------------------------------------

    def _place_seed(self, col: int, row: int, color: CellColor) -> bool:
        if self.energy <= 0:
            return False
        if self.grid[row][col].alive:
            return False
        self.grid[row][col] = Cell(alive=True, color=color, tier=1)
        self.energy -= 1
        return True

    def _can_place(self) -> bool:
        return self.energy > 0

    # ------------------------------------------------------------------
    # Evolution (Conway step)
    # ------------------------------------------------------------------

    def _evolve_generation(self) -> None:
        self.generation += 1
        new_grid: list[list[Cell]] = []
        for row in range(GRID_ROWS):
            new_row: list[Cell] = []
            for col in range(GRID_COLS):
                count, maj_color = self._count_neighbors(col, row)
                current = self.grid[row][col]
                if current.alive and current.color is not None:
                    if 2 <= count <= 3:
                        new_row.append(
                            Cell(
                                alive=True,
                                color=current.color,
                                tier=current.tier,
                            )
                        )
                    else:
                        new_row.append(Cell())
                else:
                    if count == 3 and maj_color is not None:
                        new_row.append(
                            Cell(alive=True, color=maj_color, tier=1)
                        )
                    else:
                        new_row.append(Cell())
            new_grid.append(new_row)
        self.grid = new_grid

    # ------------------------------------------------------------------
    # BFS cluster detection
    # ------------------------------------------------------------------

    def _neighbors_4(self, col: int, row: int) -> list[tuple[int, int]]:
        return [
            (col, row - 1),
            (col - 1, row),
            (col + 1, row),
            (col, row + 1),
        ]

    def _bfs_cluster(
        self, start_col: int, start_row: int, color: CellColor
    ) -> set[tuple[int, int]]:
        queue = [(start_col, start_row)]
        visited: set[tuple[int, int]] = set()
        visited.add((start_col, start_row))
        while queue:
            c, r = queue.pop(0)
            for nc, nr in self._neighbors_4(c, r):
                if not self._in_bounds(nc, nr):
                    continue
                if (nc, nr) in visited:
                    continue
                cell = self.grid[nr][nc]
                if cell.alive and cell.color == color:
                    visited.add((nc, nr))
                    queue.append((nc, nr))
        return visited

    def _find_synthesis_clusters(
        self,
    ) -> list[tuple[set[tuple[int, int]], CellColor]]:
        visited: set[tuple[int, int]] = set()
        clusters: list[tuple[set[tuple[int, int]], CellColor]] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if (col, row) in visited:
                    continue
                cell = self.grid[row][col]
                if not cell.alive or cell.color is None:
                    continue
                cluster = self._bfs_cluster(col, row, cell.color)
                visited.update(cluster)
                if len(cluster) >= SYNTHESIS_THRESHOLD:
                    clusters.append((cluster, cell.color))
        return clusters

    # ------------------------------------------------------------------
    # Synthesis processing
    # ------------------------------------------------------------------

    def _cluster_center(
        self, cluster: set[tuple[int, int]]
    ) -> tuple[int, int]:
        if not cluster:
            return 0, 0
        cx = sum(c for c, _ in cluster) // len(cluster)
        cy = sum(r for _, r in cluster) // len(cluster)
        return cx, cy

    def _process_synthesis(
        self, cluster: set[tuple[int, int]], color: CellColor
    ) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        cx, cy = self._cluster_center(cluster)
        target_cell = self.grid[cy][cx]
        old_tier = target_cell.tier
        new_tier = min(old_tier + 1, MAX_TIER + 1)

        for cc, cr in cluster:
            self.grid[cr][cc] = Cell()

        if new_tier <= MAX_TIER:
            self.grid[cy][cx] = Cell(alive=True, color=color, tier=new_tier)
            if new_tier > self.max_tier:
                self.max_tier = new_tier

        self.synthesis_events.append(
            SynthesisEvent(
                cx=cx,
                cy=cy,
                color=color,
                new_tier=new_tier,
                cluster_size=len(cluster),
                timer=SYNTH_DELAY,
            )
        )

        px, py = cell_to_pixel(cx, cy)
        self._spawn_synthesis_particles(
            px + CELL_SIZE // 2,
            py + CELL_SIZE // 2,
            color,
            len(cluster) * 4,
        )

        score_gain = self._calculate_score_for_synthesis(
            new_tier, len(cluster)
        )
        self.score += score_gain
        self.floating_texts.append(
            FloatingText(
                x=float(px + CELL_SIZE // 2),
                y=float(py),
                text=f"+{score_gain}",
                life=30,
                color=WHITE,
            )
        )

        if new_tier <= MAX_TIER:
            self._chain_explode(cx, cy, color)

    def _chain_explode(self, cx: int, cy: int, color: CellColor) -> None:
        for dc, dr in _NEIGHBOUR_OFFSETS:
            nc, nr = cx + dc, cy + dr
            if not self._in_bounds(nc, nr):
                continue
            cell = self.grid[nr][nc]
            if cell.alive:
                cell.color = color
                cell.tier = 1
            else:
                self.grid[nr][nc] = Cell(alive=True, color=color, tier=1)
            px, py = cell_to_pixel(nc, nr)
            self._spawn_synthesis_particles(
                px + CELL_SIZE // 2,
                py + CELL_SIZE // 2,
                color,
                8,
            )

    # ------------------------------------------------------------------
    # Overpopulation
    # ------------------------------------------------------------------

    def _check_overpopulation(self) -> int:
        heat_gained = 0
        for row in range(GRID_ROWS - 2):
            for col in range(GRID_COLS - 2):
                live_count = 0
                for dr in range(3):
                    for dc in range(3):
                        cr = row + dr
                        cc = col + dc
                        if self.grid[cr][cc].alive:
                            live_count += 1
                if live_count >= OVERPOP_THRESHOLD:
                    heat_gained += 1
        self.heat += heat_gained
        if self.heat >= HEAT_LIMIT:
            self._trigger_heat_reset()
        return heat_gained

    def _trigger_heat_reset(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if self.grid[row][col].alive:
                    px, py = cell_to_pixel(col, row)
                    self._spawn_synthesis_particles(
                        px + CELL_SIZE // 2,
                        py + CELL_SIZE // 2,
                        self.grid[row][col].color or CellColor.RED,
                        3,
                    )
        self._init_grid()
        self.energy = min(self.energy + 3, MAX_ENERGY)
        self.heat = 0
        self.floating_texts.append(
            FloatingText(
                x=160.0,
                y=120.0,
                text="OVERLOAD! +3 ENERGY",
                life=60,
                color=ORANGE,
            )
        )

    # ------------------------------------------------------------------
    # Score
    # ------------------------------------------------------------------

    def _calculate_score_for_synthesis(
        self, new_tier: int, cluster_size: int
    ) -> int:
        t = min(new_tier, MAX_TIER)
        return t * cluster_size * max(self.generation, 1)

    def _calculate_score(self) -> int:
        return self.score

    # ------------------------------------------------------------------
    # Game-over
    # ------------------------------------------------------------------

    def _is_game_over(self) -> bool:
        if self.energy > 0:
            return False
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cell = self.grid[row][col]
                if not cell.alive or cell.color is None:
                    continue
                count, _ = self._count_neighbors(col, row)
                if count == 2 or count == 3:
                    return False
                for dc, dr in _NEIGHBOUR_OFFSETS:
                    nc, nr = col + dc, row + dr
                    if not self._in_bounds(nc, nr):
                        continue
                    ncell = self.grid[nr][nc]
                    if not ncell.alive:
                        ncount, _ = self._count_neighbors(nc, nr)
                        if ncount == 3:
                            return False
        clusters = self._find_synthesis_clusters()
        return len(clusters) == 0

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------

    def _advance_phase(self) -> None:
        if self.phase == Phase.TITLE:
            self.phase = Phase.SEED
            self._evolve_timer = 0
            self._synth_timer = 0
        elif self.phase == Phase.SEED:
            self.phase = Phase.EVOLVING
            self._evolve_timer = EVOLVE_DELAY
            self.combo = 0
        elif self.phase == Phase.EVOLVING:
            self._check_overpopulation()
            clusters = self._find_synthesis_clusters()
            if clusters:
                self.phase = Phase.SYNTHESIS
                for cluster, color in clusters:
                    self._process_synthesis(cluster, color)
                self._synth_timer = SYNTH_DELAY
            elif self._is_game_over():
                self.phase = Phase.GAME_OVER
                self._game_over_timer = 60
            else:
                self.phase = Phase.SEED
                self._synth_timer = 0
        elif self.phase == Phase.SYNTHESIS:
            clusters = self._find_synthesis_clusters()
            if clusters:
                for cluster, color in clusters:
                    self._process_synthesis(cluster, color)
                self._synth_timer = SYNTH_DELAY
            elif self._is_game_over():
                self.phase = Phase.GAME_OVER
                self._game_over_timer = 60
            else:
                self.phase = Phase.SEED
                self._synth_timer = 0

    # ------------------------------------------------------------------
    # Phase-specific updates
    # ------------------------------------------------------------------

    def update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._advance_phase()

    def update_seed(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        cell_pos = pixel_to_cell(mx, my)
        if cell_pos is not None:
            self.mouse_cx, self.mouse_cy = cell_pos
        else:
            self.mouse_cx = -1
            self.mouse_cy = -1

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._advance_phase()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if cell_pos is not None:
                col, row = cell_pos
                color = list(CellColor)[
                    (col + row) % len(CellColor)
                ]
                self._place_seed(col, row, color)

            evolve_btn_x = 320 - 60
            evolve_btn_y = HUD_Y + 2
            evolve_btn_w = 56
            evolve_btn_h = 20
            if (
                evolve_btn_x <= mx <= evolve_btn_x + evolve_btn_w
                and evolve_btn_y <= my <= evolve_btn_y + evolve_btn_h
            ):
                self._advance_phase()

    def update_evolving(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_synthesis_events()
        self._evolve_timer -= 1
        if self._evolve_timer <= 0:
            self._evolve_generation()
            self._advance_phase()

    def update_synthesis(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_synthesis_events()
        self._synth_timer -= 1
        if self._synth_timer <= 0:
            self._advance_phase()

    def update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._game_over_timer -= 1
        if self._game_over_timer <= 0 and (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()
        elif pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(
            pyxel.MOUSE_BUTTON_LEFT
        ):
            self.reset()

    # ------------------------------------------------------------------
    # Particle & floating text updates
    # ------------------------------------------------------------------

    def _spawn_synthesis_particles(
        self, px: float, py: float, color: CellColor, count: int
    ) -> None:
        pcolor = tier_color(color, 3)
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(
                Particle(
                    x=px,
                    y=py,
                    vx=vx,
                    vy=vy,
                    life=self._rng.randint(10, 25),
                    color=pcolor,
                    size=self._rng.uniform(2.0, 4.0),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            p.size = max(0.5, p.size - 0.3)
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.floating_texts = [
            ft for ft in self.floating_texts if ft.life > 0
        ]

    def _update_synthesis_events(self) -> None:
        for se in self.synthesis_events:
            se.timer -= 1
        self.synthesis_events = [
            se for se in self.synthesis_events if se.timer > 0
        ]

    # ------------------------------------------------------------------
    # Global update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        match self.phase:
            case Phase.TITLE:
                self.update_title()
            case Phase.SEED:
                self.update_seed()
            case Phase.EVOLVING:
                self.update_evolving()
            case Phase.SYNTHESIS:
                self.update_synthesis()
            case Phase.GAME_OVER:
                self.update_game_over()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw_grid(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x, y = cell_to_pixel(col, row)
                cell = self.grid[row][col]
                if cell.alive and cell.color is not None:
                    pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, tier_color(cell.color, cell.tier))
                else:
                    pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, NAVY)

        if self.phase == Phase.SEED:
            if self._in_bounds(self.mouse_cx, self.mouse_cy):
                mx, my = cell_to_pixel(self.mouse_cx, self.mouse_cy)
                cell = self.grid[self.mouse_cy][self.mouse_cx]
                if not cell.alive and self.energy > 0:
                    pyxel.rectb(mx, my, CELL_SIZE, CELL_SIZE, WHITE)

    def _draw_synthesis_animations(self) -> None:
        for se in self.synthesis_events:
            if se.timer <= 0:
                continue
            px, py = cell_to_pixel(se.cx, se.cy)
            flash = se.timer % 6 < 3
            if flash and se.new_tier <= MAX_TIER:
                tc = tier_color(se.color, se.new_tier)
                pyxel.rect(
                    px, py, CELL_SIZE, CELL_SIZE,
                    WHITE if se.timer % 4 < 2 else tc,
                )
            radius = (SYNTH_DELAY - se.timer) // 2
            pyxel.circb(
                px + CELL_SIZE // 2,
                py + CELL_SIZE // 2,
                min(radius, 30),
                tier_color(se.color, 2),
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            c = p.color if alpha > 0.5 else (GRAY if alpha > 0.25 else NAVY)
            s = int(max(1, p.size))
            pyxel.rect(int(p.x) - s // 2, int(p.y) - s // 2, s, s, c)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            c = ft.color if alpha > 0.5 else GRAY
            pyxel.text(
                int(ft.x) - len(ft.text) * 2,
                int(ft.y),
                ft.text,
                c,
            )

    def _draw_hud(self) -> None:
        pyxel.rect(0, HUD_Y, 320, HUD_HEIGHT, NAVY)
        pyxel.line(0, HUD_Y, 320, HUD_Y, GRAY)

        pyxel.text(4, HUD_Y + 2, f"E:{self.energy}", YELLOW)

        heat_color = RED if self.heat >= 4 else ORANGE
        heat_text = f"H:{self.heat}"
        pyxel.text(54, HUD_Y + 2, heat_text, heat_color)
        if self.heat >= 4 and pyxel.frame_count % 30 < 15:
            pyxel.text(54, HUD_Y + 2, heat_text, WHITE)

        pyxel.text(94, HUD_Y + 2, f"S:{self.score}", WHITE)
        pyxel.text(160, HUD_Y + 2, f"G:{self.generation}", CYAN)
        pyxel.text(210, HUD_Y + 2, f"C:{self.combo}", PINK)
        pyxel.text(250, HUD_Y + 2, f"T:{self.max_tier}", ORANGE)

        btn_x = 320 - 60
        btn_y = HUD_Y + 2
        btn_w = 56
        btn_h = 20
        hover = False
        if self.phase == Phase.SEED:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            hover = (
                btn_x <= mx <= btn_x + btn_w
                and btn_y <= my <= btn_y + btn_h
            )
        btn_col = LIME if hover else GREEN
        pyxel.rectb(btn_x, btn_y, btn_w, btn_h, btn_col)
        pyxel.text(btn_x + 8, btn_y + 4, "EVOLVE", btn_col)

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(110, 60, "CELL FORGE", WHITE)
        pyxel.text(90, 80, "Conway + Alchemy Synthesis", GRAY)
        pyxel.text(116, 110, "Click to Start", YELLOW)
        pyxel.text(60, 150, "Controls:", WHITE)
        pyxel.text(60, 165, "Click cells -> Place seeds", GRAY)
        pyxel.text(60, 178, "SPACE / EVOLVE btn -> Evolve", GRAY)
        pyxel.text(60, 191, "R -> Restart anytime", GRAY)
        pyxel.text(50, 220, "Place seeds, evolve, chain-synthesize!", CYAN)

    def _draw_game(self) -> None:
        pyxel.cls(BLACK)
        self._draw_grid()
        self._draw_synthesis_animations()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        self._draw_game()
        overlay = DARK_BLUE
        pyxel.rect(0, 0, 320, 240, overlay)
        pyxel.text(110, 50, "GAME OVER", RED)
        pyxel.text(100, 75, f"Score: {self.score}", WHITE)
        pyxel.text(100, 90, f"Max Tier: {self.max_tier}", ORANGE)
        pyxel.text(100, 105, f"Generations: {self.generation}", CYAN)
        pyxel.text(100, 120, f"Max Combo: {self.max_combo}", PINK)
        pyxel.text(80, 170, "Click or SPACE to Retry", YELLOW)

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.SEED | Phase.EVOLVING | Phase.SYNTHESIS:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game_over()


# ---------------------------------------------------------------------------
# App wrapper
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="CELL FORGE", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
