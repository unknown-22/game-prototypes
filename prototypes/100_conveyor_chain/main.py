"""100_conveyor_chain -- Factory Conveyor Belt Color-Match Puzzle

The most fun moment:
    同じ色のアイテムがコンベア上で連鎖し、合成されて爆発的に得点が伸びる
    (Same-color items chain on the conveyor belt, merging into explosive score bursts)

Core loop: Items flow along conveyor belt tiles through an 8x8 grid.
Player clicks to rotate tiles 90°, optimizing routes to matching output bins.
Adjacent same-color items form chains. Chain length >= 3 triggers COMBO --
lead item becomes SUPER (rainbow, 3x score). Wrong bin = HEAT. HEAT max = game over.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240

COLS = 8
ROWS = 8
CELL = 26
GRID_X = 56
GRID_Y = 24
ITEM_SIZE = 14

MAX_HEAT = 100
CHAIN_THRESHOLD = 3
SUPER_SCORE_MULT = 3
SPAWN_INTERVAL_INIT = 60
SPAWN_INTERVAL_MIN = 15
DIFFICULTY_INTERVAL = 600

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

ITEM_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
ITEM_COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]
RAINBOW_COLORS: list[int] = [RED, ORANGE, YELLOW, GREEN, CYAN, PURPLE]

DIR_DELTAS: list[tuple[int, int]] = [(1, 0), (0, 1), (-1, 0), (0, -1)]
DIR_4: list[tuple[int, int]] = [(0, -1), (0, 1), (-1, 0), (1, 0)]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class BeltTile:
    col: int
    row: int
    direction: int  # 0=right, 1=down, 2=left, 3=up


@dataclass
class Item:
    col: int
    row: int
    color: int
    chained: bool = False
    super_item: bool = False
    chain_pos: int = 0


@dataclass
class OutputBin:
    col: int
    target_color: int


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Core game logic. Headless-testable via Game.__new__ bypass."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="100 Conveyor Chain", display_scale=2)
        pyxel.mouse(True)
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.tiles: list[list[BeltTile]] = []
        self.items: list[Item] = []
        self.bins: list[OutputBin] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.super_count: int = 0
        self.spawn_interval: int = SPAWN_INTERVAL_INIT
        self.spawn_timer: int = 0
        self.difficulty_timer: int = 0
        self.game_timer: int = 0
        self._active_colors: list[int] = [0, 1]  # color indices unlocked

    def reset(self) -> None:
        self._init_state()
        self._init_tiles()
        self._init_bins()

    def _init_tiles(self) -> None:
        self.tiles = [
            [BeltTile(col=c, row=r, direction=1) for c in range(COLS)]
            for r in range(ROWS)
        ]

    def _init_bins(self) -> None:
        targets = self._rng.sample([0, 1, 2, 3], 4)
        cols = self._rng.sample(range(COLS), 4)
        self.bins = [
            OutputBin(col=cols[i], target_color=targets[i]) for i in range(4)
        ]

    # ------------------------------------------------------------------
    # Testable logic (no pyxel dependency)
    # ------------------------------------------------------------------

    def _rotate_tile(self, col: int, row: int) -> None:
        t = self.tiles[row][col]
        t.direction = (t.direction + 1) % 4

    def _item_direction(self, item: Item) -> tuple[int, int]:
        d = self.tiles[item.row][item.col].direction
        return DIR_DELTAS[d]

    def _move_items(self) -> None:
        """Move all items one step along their tile's conveyor direction."""
        for item in self.items:
            dc, dr = self._item_direction(item)
            item.col += dc
            item.row += dr

    def _check_bin_arrival(self) -> list[tuple[Item, OutputBin | None]]:
        """Return list of (item, bin) for items that left the grid.
        bin is None if no matching bin under the column."""
        results: list[tuple[Item, OutputBin | None]] = []
        for item in self.items:
            if item.row >= ROWS or item.row < 0 or item.col < 0 or item.col >= COLS:
                matched_bin = self._get_bin_at(item.col)
                results.append((item, matched_bin))
        return results

    def _get_bin_at(self, col: int) -> OutputBin | None:
        for b in self.bins:
            if b.col == col:
                return b
        return None

    def _process_arrival(self, item: Item, bin_: OutputBin | None) -> int:
        """Process item arrival at output. Returns score gained."""
        if item.super_item:
            gained = 10 * SUPER_SCORE_MULT * max(1, self.combo)
            self.score += gained
            self.super_count += 1
            return gained

        if bin_ is not None and item.color == bin_.target_color:
            gained = 10 * max(1, self.combo)
            self.score += gained
            return gained

        self.heat = min(self.heat + 15, MAX_HEAT)
        return 0

    def _detect_chains(self) -> None:
        """BFS-detect adjacent same-color items and mark chains."""
        item_set: set[int] = set(range(len(self.items)))
        processed: set[int] = set()

        for i, item in enumerate(self.items):
            item.chained = False
            item.chain_pos = 0

        chains: list[list[int]] = []
        while item_set - processed:
            seed = next(iter(item_set - processed))
            visited: set[int] = {seed}
            queue: list[int] = [seed]
            while queue:
                cur = queue.pop()
                cur_item = self.items[cur]
                for other in item_set - visited:
                    if other in processed:
                        continue
                    o_item = self.items[other]
                    if cur_item.color == o_item.color:
                        if cur_item.col == o_item.col and abs(cur_item.row - o_item.row) == 1:
                            visited.add(other)
                            queue.append(other)
                        elif cur_item.row == o_item.row and abs(cur_item.col - o_item.col) == 1:
                            visited.add(other)
                            queue.append(other)
            processed |= visited
            if len(visited) >= 2:
                chains.append(list(visited))

        for chain in chains:
            for idx, item_idx in enumerate(chain):
                self.items[item_idx].chained = True
                self.items[item_idx].chain_pos = idx

    def _process_chains(self) -> None:
        """Check chains for COMBO threshold. Promote lead items to SUPER."""
        chains_by_color: dict[int, list[list[int]]] = {}
        for i, item in enumerate(self.items):
            if not item.chained:
                continue
            c = item.color
            if c not in chains_by_color:
                chains_by_color[c] = []
            found = False
            for chain in chains_by_color[c]:
                if i in chain:
                    found = True
                    break
            if not found:
                visited: set[int] = {i}
                queue: list[int] = [i]
                while queue:
                    cur = queue.pop()
                    cur_item = self.items[cur]
                    for j in range(len(self.items)):
                        if j in visited:
                            continue
                        o_item = self.items[j]
                        if o_item.color != c or not o_item.chained:
                            continue
                        if cur_item.col == o_item.col and abs(cur_item.row - o_item.row) == 1:
                            visited.add(j)
                            queue.append(j)
                        elif cur_item.row == o_item.row and abs(cur_item.col - o_item.col) == 1:
                            visited.add(j)
                            queue.append(j)
                chain_ids = list(visited)
                chains_by_color[c].append(chain_ids)

        for chains in chains_by_color.values():
            for chain in chains:
                if len(chain) >= CHAIN_THRESHOLD:
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    self.score += self.combo * 5
                    lead = self.items[chain[0]]
                    lead.super_item = True
                    self._spawn_combo_particles(lead)

    def _spawn_item(self) -> Item | None:
        color_idx = self._rng.choice(self._active_colors)
        col = self._rng.randint(0, COLS - 1)
        # Don't spawn if cell occupied
        for item in self.items:
            if item.col == col and item.row == 0:
                return None
        return Item(col=col, row=0, color=color_idx)

    def _update_difficulty(self) -> None:
        self.difficulty_timer += 1
        if self.difficulty_timer >= DIFFICULTY_INTERVAL:
            self.difficulty_timer = 0
            self.spawn_interval = max(SPAWN_INTERVAL_MIN, self.spawn_interval - 3)
            if len(self._active_colors) < 4:
                unused = [c for c in [0, 1, 2, 3] if c not in self._active_colors]
                if unused:
                    self._active_colors.append(self._rng.choice(unused))

    def _update_heat_passive(self) -> None:
        if self.game_timer % 60 == 0:
            self.heat = min(self.heat + 1, MAX_HEAT)

    def _check_game_over(self) -> bool:
        return self.heat >= MAX_HEAT

    # ------------------------------------------------------------------
    # Particles & Effects
    # ------------------------------------------------------------------

    def _spawn_combo_particles(self, item: Item) -> None:
        px = GRID_X + item.col * CELL + CELL // 2
        py = GRID_Y + item.row * CELL + CELL // 2
        color = RAINBOW_COLORS[self._rng.randint(0, len(RAINBOW_COLORS) - 1)]
        for _ in range(6):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x=px, y=py,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(10, 20),
                    color=color,
                )
            )

    def _spawn_super_burst(self, item: Item) -> None:
        px = GRID_X + item.col * CELL + CELL // 2
        py = GRID_Y + item.row * CELL + CELL // 2
        for _ in range(12):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            rainbow_c = RAINBOW_COLORS[self._rng.randint(0, len(RAINBOW_COLORS) - 1)]
            self.particles.append(
                Particle(
                    x=px, y=py,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(15, 25),
                    color=rainbow_c,
                )
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=20, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.95
            p.vy *= 0.95
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.game_timer += 1

        # Mouse click to rotate tile
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            col = (mx - GRID_X) // CELL
            row = (my - GRID_Y) // CELL
            if 0 <= col < COLS and 0 <= row < ROWS:
                self._rotate_tile(col, row)

        # Spawn items
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            new_item = self._spawn_item()
            if new_item is not None:
                self.items.append(new_item)

        # Move items
        self._move_items()

        # Check bin arrivals
        arrivals = self._check_bin_arrival()
        arrived_items: list[Item] = []
        for item, bin_ in arrivals:
            if item.super_item:
                px = GRID_X + item.col * CELL + CELL // 2
                py = GRID_Y + (ROWS - 1) * CELL + CELL
                self._spawn_super_burst(item)
                self._add_floating_text(px, py - 10, f"+{10 * SUPER_SCORE_MULT * max(1, self.combo)}", YELLOW)
            self._process_arrival(item, bin_)
            arrived_items.append(item)

        # Remove arrived items
        self.items = [it for it in self.items if it not in arrived_items]

        # Detect and process chains
        self._detect_chains()
        self._process_chains()

        # Difficulty
        self._update_difficulty()

        # Passive heat
        self._update_heat_passive()

        # Check game over
        if self._check_game_over():
            self.phase = Phase.GAME_OVER

        self._update_particles()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _cell_rect(self, col: int, row: int, margin: int = 0) -> tuple[int, int, int, int]:
        x = GRID_X + col * CELL + margin
        y = GRID_Y + row * CELL + margin
        w = CELL - margin * 2
        return x, y, w, w

    def _draw_grid(self) -> None:
        pyxel.rect(GRID_X - 1, GRID_Y - 1, COLS * CELL + 2, ROWS * CELL + 2, WHITE)
        pyxel.rect(GRID_X, GRID_Y, COLS * CELL, ROWS * CELL, NAVY)
        for r in range(ROWS):
            for c in range(COLS):
                x, y, w, _ = self._cell_rect(c, r, 1)
                pyxel.rect(x, y, w, w, DARK_BLUE)

    def _draw_tiles(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                t = self.tiles[r][c]
                cx = GRID_X + c * CELL + CELL // 2
                cy = GRID_Y + r * CELL + CELL // 2
                s = 6
                if t.direction == 0:  # right
                    pyxel.tri(cx + s, cy, cx - s, cy - s, cx - s, cy + s, GRAY)
                elif t.direction == 1:  # down
                    pyxel.tri(cx, cy + s, cx - s, cy - s, cx + s, cy - s, GRAY)
                elif t.direction == 2:  # left
                    pyxel.tri(cx - s, cy, cx + s, cy - s, cx + s, cy + s, GRAY)
                elif t.direction == 3:  # up
                    pyxel.tri(cx, cy - s, cx - s, cy + s, cx + s, cy + s, GRAY)

    def _draw_items(self) -> None:
        for item in self.items:
            cx = GRID_X + item.col * CELL + CELL // 2
            cy = GRID_Y + item.row * CELL + CELL // 2
            half = ITEM_SIZE // 2
            col = ITEM_COLORS[item.color]
            pyxel.rect(cx - half, cy - half, ITEM_SIZE, ITEM_SIZE, col)
            if item.super_item:
                rainbow_idx = (pyxel.frame_count // 4) % len(RAINBOW_COLORS)
                rcol = RAINBOW_COLORS[rainbow_idx]
                pyxel.rectb(cx - half - 1, cy - half - 1, ITEM_SIZE + 2, ITEM_SIZE + 2, rcol)
            else:
                pyxel.rectb(cx - half, cy - half, ITEM_SIZE, ITEM_SIZE, WHITE)

    def _draw_chain_links(self) -> None:
        for i, a in enumerate(self.items):
            if not a.chained:
                continue
            for b in self.items[i + 1:]:
                if not b.chained or a.color != b.color:
                    continue
                if a.col == b.col and abs(a.row - b.row) == 1:
                    ax = GRID_X + a.col * CELL + CELL // 2
                    ay = GRID_Y + a.row * CELL + CELL // 2
                    bx = GRID_X + b.col * CELL + CELL // 2
                    by = GRID_Y + b.row * CELL + CELL // 2
                    pyxel.line(ax, ay, bx, by, ITEM_COLORS[a.color])
                elif a.row == b.row and abs(a.col - b.col) == 1:
                    ax = GRID_X + a.col * CELL + CELL // 2
                    ay = GRID_Y + a.row * CELL + CELL // 2
                    bx = GRID_X + b.col * CELL + CELL // 2
                    by = GRID_Y + b.row * CELL + CELL // 2
                    pyxel.line(ax, ay, bx, by, ITEM_COLORS[a.color])

    def _draw_bins(self) -> None:
        for b in self.bins:
            bx = GRID_X + b.col * CELL + 2
            by = GRID_Y + ROWS * CELL + 2
            bw = CELL - 4
            bh = 10
            col = ITEM_COLORS[b.target_color]
            pyxel.rect(bx, by, bw, bh, col)
            pyxel.rectb(bx, by, bw, bh, WHITE)

    def _draw_heat_bar(self) -> None:
        bar_x = GRID_X
        bar_y = GRID_Y - 10
        bar_w = COLS * CELL
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill_w = int(bar_w * self.heat / MAX_HEAT)
        if self.heat < 50:
            hcol = LIME
        elif self.heat < 80:
            hcol = ORANGE
        else:
            hcol = RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, hcol)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x, bar_y - 8, "HEAT", GRAY)

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)

        # Combo (top-right)
        combo_text = f"COMBO:{self.combo}"
        cw = len(combo_text) * 4
        if self.combo >= CHAIN_THRESHOLD:
            cc = YELLOW
        elif self.combo >= 1:
            cc = ORANGE
        else:
            cc = GRAY
        pyxel.text(SCREEN_W - cw - 4, 4, combo_text, cc)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            c = p.color if alpha > 0.2 else GRAY
            pyxel.rect(int(p.x), int(p.y), 2, 2, c)
        for ft in self.floating_texts:
            alpha = ft.life / 20.0
            if alpha > 0.3:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_title(self) -> None:
        title = "CONVEYOR CHAIN"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 30, title, WHITE)

        sub = "Factory Belt Puzzle"
        sw = len(sub) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 44, sub, LIME)

        # Color legend
        for i, (col, name) in enumerate(zip(ITEM_COLORS, ITEM_COLOR_NAMES)):
            bx = 25 + i * 70
            pyxel.rect(bx, 62, 16, 16, col)
            pyxel.rectb(bx, 62, 16, 16, WHITE)
            nw = len(name) * 4
            pyxel.text(bx + 8 - nw // 2, 82, name, WHITE)

        lines = [
            "Items flow along conveyor belts.",
            "Click tiles to rotate direction!",
            "",
            f"Chain {CHAIN_THRESHOLD}+ same-color items",
            "  -> COMBO! Lead becomes SUPER",
            "  (rainbow, 3x score multiplier)",
            "",
            "Match item color to output bin",
            "Wrong bin = +HEAT",
            "HEAT 100% = GAME OVER (overheat!)",
            "",
            "SPACE or ENTER to START",
        ]
        for i, ln in enumerate(lines):
            pyxel.text(14, 104 + i * 10, ln, GRAY)

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_tiles()
        self._draw_chain_links()
        self._draw_items()
        self._draw_bins()
        self._draw_heat_bar()
        self._draw_hud()
        self._draw_particles()

    def _draw_game_over(self) -> None:
        self._draw_grid()
        self._draw_tiles()
        self._draw_items()
        self._draw_bins()
        self._draw_particles()

        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        go_text = "OVERHEAT!"
        gw = len(go_text) * 4
        flash = (pyxel.frame_count // 10) % 2 == 0
        pyxel.text(SCREEN_W // 2 - gw // 2, 40, go_text, RED if flash else ORANGE)

        def _ctr(y: int, text: str, color: int) -> None:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)

        _ctr(70, f"SCORE: {self.score}", WHITE)
        _ctr(90, f"MAX COMBO: {self.max_combo}", ORANGE)
        _ctr(110, f"SUPER ITEMS: {self.super_count}", YELLOW)
        _ctr(130, f"TIME: {self.game_timer // 30}s", GRAY)

        _ctr(170, "Press R to RETRY", GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
