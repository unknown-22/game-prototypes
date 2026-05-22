"""CHAIN PUSH — Sokoban-style block pushing with synthesis merge and CA chain spread.

Core mechanic: Push same-color blocks together to merge (SYNTHESIS) and trigger
color-spread chain reactions across adjacent blocks. Cascading chains create
massive combo multipliers.

Genre: Sokoban / block-pushing puzzle (NEW to the collection)
Reinterpreted from: Idea #1 Score 32.75 (deckbuilder roguelite, alchemy synthesis)
Transfer hooks: "synthesis compression" → same-color block merge
                "CA grid spread" → merged block color propagation to neighbors

Controls:
  Arrow/WASD: Move / push blocks
  R: Restart level
  SPACE/RETURN: Start game / advance
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──
SCREEN_W = 256
SCREEN_H = 256
COLS = 8
ROWS = 8
CELL = 32
GRID_OX = 0
GRID_OY = 0

# Colors (pyxel ints): RED=8, GREEN=11, DARK_BLUE=5, YELLOW=10
COLOR_INTS: tuple[int, ...] = (8, 11, 5, 10)
NUM_COLORS: int = len(COLOR_INTS)
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")

TIER_MAX: int = 3
TIER_VALUES: tuple[int, ...] = (0, 10, 30, 90)  # index by tier
TIER_SIZES: tuple[int, ...] = (0, 8, 14, 20)  # half-size for drawing

PARTICLE_COUNT: int = 6
PARTICLE_LIFE: int = 15
LEVEL_CLEAR_DELAY: int = 60
RESOLVE_DELAY: int = 3  # frames between chain steps (visual pacing)
TITLE_BLINK: int = 30

# ── Phase ──


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    RESOLVING = auto()
    LEVEL_CLEAR = auto()
    GAME_OVER = auto()
    VICTORY = auto()


# ── Data ──


@dataclass
class Block:
    col: int
    row: int
    color: int  # 0-3 index
    tier: int  # 1-3


@dataclass
class Target:
    col: int
    row: int
    color: int  # -1 = any color, 0-3 = specific color


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Level definitions ──
# Each level: (blocks, targets, player_pos)
# Blocks: list of (col, row, color, tier)
# Targets: list of (col, row, color) — color=-1 means any
# Player: (col, row)

LEVEL_DEFS: list[dict] = [
    {  # Level 1: "First Merge" — learn push + merge (1 push to win)
        "blocks": [
            (1, 3, 0, 1),  # RED T1 at (1,3)
            (3, 3, 0, 1),  # RED T1 at (3,3) — gap at (2,3)
        ],
        "targets": [
            (3, 3, 0),  # RED target at survivor position
        ],
        "player": (0, 3),
    },
    {  # Level 2: "Chain Spread" — 2-step chain: merge→spread→merge→T3
        "blocks": [
            (1, 2, 0, 1),  # RED T1 at (1,2) — push right to (2,2)
            (3, 2, 0, 1),  # RED T1 at (3,2) — merge with above → T2
            (3, 3, 2, 1),  # BLUE T1 at (3,3) — spread→RED, then chain-merge→T3
            (5, 3, 1, 1),  # GREEN T1 at (5,3) — separate pair
            (5, 5, 1, 1),  # GREEN T1 at (5,5)
        ],
        "targets": [
            (3, 2, 0),  # RED T3 at survivor
            (5, 5, -1),  # any color at GREEN T2 position
        ],
        "player": (0, 3),
    },
    {  # Level 3: "T3 Supernova" — T3 8-direction spread (2-step chain)
        "blocks": [
            (1, 2, 0, 1),  # RED T1 at (1,2) — push right
            (3, 2, 0, 1),  # RED T1 at (3,2) — merge → T2
            (3, 3, 2, 1),  # BLUE T1 at (3,3) — spread→RED, chain merge→T3
            (2, 1, 2, 1),  # BLUE T1 at (2,1) — T3 diagonal spread→RED
            (4, 1, 1, 1),  # GREEN T1 at (4,1) — T3 diagonal spread→RED
            (5, 5, 3, 1),  # YELLOW T1 at (5,5) — spectator
        ],
        "targets": [
            (3, 2, 0),  # T3 RED at survivor
            (2, 1, 0),  # BLUE→RED from T3 diagonal spread
            (4, 1, -1),  # GREEN→RED from T3 spread
        ],
        "player": (0, 2),
    },
    {  # Level 4: "Tactical Planning" — 4 color pairs, choose order
        "blocks": [
            (1, 1, 0, 1),  # RED pair, gap at (2,1)
            (3, 1, 0, 1),
            (1, 5, 1, 1),  # GREEN pair, gap at (2,5)
            (3, 5, 1, 1),
            (5, 1, 2, 1),  # BLUE pair, gap at (6,1)
            (7, 1, 2, 1),
            (5, 5, 3, 1),  # YELLOW pair, gap at (6,5)
            (7, 5, 3, 1),
            (4, 3, 0, 1),  # RED near center
        ],
        "targets": [
            (3, 1, 0),
            (3, 5, 1),
            (7, 1, 2),
            (7, 5, 3),
            (4, 3, -1),
        ],
        "player": (0, 3),
    },
    {  # Level 5: "Grand Cascade" — many blocks, potential for huge chains
        "blocks": [
            (1, 1, 0, 1),  # RED pair A
            (3, 1, 0, 1),
            (1, 3, 1, 1),  # GREEN pair
            (3, 3, 1, 1),
            (1, 5, 2, 1),  # BLUE pair
            (3, 5, 2, 1),
            (5, 1, 3, 1),  # YELLOW pair
            (5, 3, 3, 1),
            (5, 5, 0, 1),  # RED pair B
            (7, 5, 0, 1),
            (4, 2, 2, 1),  # BLUE near center (spread target)
            (4, 4, 1, 1),  # GREEN near center (spread target)
        ],
        "targets": [
            (3, 1, 0),
            (3, 3, 1),
            (3, 5, 2),
            (5, 1, 3),
            (7, 5, 0),
            (4, 3, -1),
        ],
        "player": (0, 0),
    },
]

# ── Game ──


class Game:
    """Main game class for CHAIN PUSH."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN PUSH")
        self._rng = random.Random()
        self.grid: list[list[Block | None]] = []
        self.targets: list[Target] = []
        self.particles: list[Particle] = []
        self._merged_blocks: list[Block] = []
        self._resolve_timer: int = 0
        self._resolve_queue: list[list[Block]] = []
        self._spread_queue: list[Block] = []
        self._level_clear_timer: int = 0
        self._title_frame: int = 0
        # State (pre-init for headless tests via Game.__new__)
        self.phase: Phase = Phase.TITLE
        self.level: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.chain_depth: int = 0
        self.moves: int = 0
        self.player_col: int = 0
        self.player_row: int = 0
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all game state."""
        self.phase = Phase.TITLE
        self.level = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.chain_depth = 0
        self.moves = 0
        self.player_col = 0
        self.player_row = 0
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.targets.clear()
        self.particles.clear()
        self._merged_blocks.clear()
        self._resolve_queue.clear()
        self._spread_queue.clear()
        self._resolve_timer = 0
        self._level_clear_timer = 0
        self._title_frame = 0

    # ── Level management ──

    def _load_level(self, level_idx: int) -> None:
        """Load a level by index (1-based)."""
        self.level = level_idx
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.targets.clear()
        self.particles.clear()
        self._merged_blocks.clear()
        self._resolve_queue.clear()
        self._spread_queue.clear()
        self._resolve_timer = 0
        self._level_clear_timer = 0
        self.combo = 0
        self.chain_depth = 0
        self.moves = 0

        if level_idx <= len(LEVEL_DEFS):
            self._load_predefined(LEVEL_DEFS[level_idx - 1])
        else:
            self._generate_procedural(level_idx)

    def _load_predefined(self, defn: dict) -> None:
        """Load a predefined level definition."""
        for col, row, color, tier in defn["blocks"]:
            self.grid[row][col] = Block(col, row, color, tier)
        for col, row, color in defn["targets"]:
            self.targets.append(Target(col, row, color))
        self.player_col, self.player_row = defn["player"]

    def _generate_procedural(self, level_idx: int) -> None:
        """Generate a procedural level for level >= 6."""
        rng = random.Random(level_idx * 137 + 42)
        num_blocks = min(level_idx + 2, COLS * ROWS - 4)
        num_targets = min(level_idx // 2 + 2, 8)

        # Place player near center
        self.player_col = COLS // 2
        self.player_row = ROWS // 2

        # Place targets
        for _ in range(num_targets):
            for _ in range(100):
                c = rng.randint(0, COLS - 1)
                r = rng.randint(0, ROWS - 1)
                if (c, r) == (self.player_col, self.player_row):
                    continue
                if any(t.col == c and t.row == r for t in self.targets):
                    continue
                self.targets.append(Target(c, r, rng.randint(-1, NUM_COLORS - 1)))
                break

        # Place blocks with bias toward pairs
        placed = 0
        for _ in range(num_blocks * 4):
            if placed >= num_blocks:
                break
            c = rng.randint(0, COLS - 1)
            r = rng.randint(0, ROWS - 1)
            if (c, r) == (self.player_col, self.player_row):
                continue
            if self.grid[r][c] is not None:
                continue
            color = rng.randint(0, NUM_COLORS - 1)
            tier = 1
            # Bias: 40% chance to place same-color adjacent to existing
            if rng.random() < 0.4:
                for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nc, nr = c + dc, r + dr
                    if self._in_bounds(nc, nr):
                        neighbor = self.grid[nr][nc]
                        if neighbor is not None:
                            color = neighbor.color
                            break
            self.grid[r][c] = Block(c, r, color, tier)
            placed += 1

    # ── Update ──

    def update(self) -> None:
        """Main update loop."""
        self._title_frame += 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.RESOLVING:
            self._update_resolving()
        elif self.phase == Phase.LEVEL_CLEAR:
            self._update_level_clear()
        elif self.phase in (Phase.GAME_OVER, Phase.VICTORY):
            self._update_game_over()

        self._update_particles()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._load_level(1)
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._load_level(self.level)
            return

        dx, dy = 0, 0
        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
            dy = -1
        elif pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            dy = 1
        elif pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            dx = -1
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            dx = 1

        if dx == 0 and dy == 0:
            return

        new_col = self.player_col + dx
        new_row = self.player_row + dy

        if not self._in_bounds(new_col, new_row):
            return

        target_cell = self.grid[new_row][new_col]

        if target_cell is None:
            self.player_col = new_col
            self.player_row = new_row
            self.moves += 1
        else:
            push_col = new_col + dx
            push_row = new_row + dy
            if self._in_bounds(push_col, push_row) and self.grid[push_row][push_col] is None:
                block = target_cell
                self.grid[new_row][new_col] = None
                self.grid[push_row][push_col] = block
                block.col = push_col
                block.row = push_row
                self.player_col = new_col
                self.player_row = new_row
                self.moves += 1
                self._start_resolve()

    def _start_resolve(self) -> None:
        """Begin the chain resolution process."""
        self.phase = Phase.RESOLVING
        self.combo = 0
        self.chain_depth = 0
        self._merged_blocks.clear()
        self._resolve_queue.clear()
        self._spread_queue.clear()
        self._resolve_timer = RESOLVE_DELAY

    def _update_resolving(self) -> None:
        """Process chain resolution step by step with visual delay."""
        self._resolve_timer -= 1
        if self._resolve_timer > 0:
            return

        # Step 1: find merge groups
        groups = self._find_merge_groups()
        if groups:
            self.chain_depth += 1
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # Merge all groups
            for group in groups:
                self._merge_group(group)

            # Queue spread
            self._spread_queue = list(self._merged_blocks)
            self._merged_blocks.clear()
            self._resolve_timer = RESOLVE_DELAY
            return

        # Step 2: do spread from queued blocks
        if self._spread_queue:
            self._do_spread(self._spread_queue)
            self._spread_queue.clear()
            self._resolve_timer = RESOLVE_DELAY
            return

        # No more merges or spreads — resolution complete
        self.phase = Phase.PLAYING
        if self._check_win():
            self.phase = Phase.LEVEL_CLEAR
            self._level_clear_timer = LEVEL_CLEAR_DELAY
            # Bonus score for clearing level
            self.score += self.level * 100
        self.combo = 0

    def _update_level_clear(self) -> None:
        self._level_clear_timer -= 1
        if self._level_clear_timer <= 0:
            if self.level < len(LEVEL_DEFS) + 5:  # predefined + 5 procedural
                self._load_level(self.level + 1)
                self.phase = Phase.PLAYING
            else:
                self.phase = Phase.VICTORY

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self._load_level(1)
            self.phase = Phase.PLAYING
        elif pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self._load_level(1)
            self.phase = Phase.PLAYING

    # ── Merge / Spread logic ──

    def _find_merge_groups(self) -> list[list[Block]]:
        """Find all groups of 2+ same-color adjacent blocks via BFS."""
        visited: set[tuple[int, int]] = set()
        groups: list[list[Block]] = []

        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) in visited:
                    continue
                block = self.grid[r][c]
                if block is None:
                    continue

                group: list[Block] = []
                queue: list[tuple[int, int]] = [(c, r)]
                visited.add((c, r))
                color = block.color

                while queue:
                    bc, br = queue.pop(0)
                    b = self.grid[br][bc]
                    if b is not None:
                        group.append(b)
                    for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                        nc, nr = bc + dc, br + dr
                        if not self._in_bounds(nc, nr) or (nc, nr) in visited:
                            continue
                        nb = self.grid[nr][nc]
                        if nb is not None and nb.color == color:
                            visited.add((nc, nr))
                            queue.append((nc, nr))

                if len(group) >= 2:
                    groups.append(group)

        return groups

    def _merge_group(self, group: list[Block]) -> None:
        """Merge a group of same-color blocks. Highest-tier absorbs others."""
        survivor = group[0]
        max_tier = survivor.tier
        for b in group:
            if b.tier > max_tier or (b.tier == max_tier and (b.row < survivor.row or (b.row == survivor.row and b.col < survivor.col))):
                survivor = b
                max_tier = b.tier

        new_tier = min(max_tier + 1, TIER_MAX)
        score_gain = TIER_VALUES[new_tier]

        # Score: base tier value × combo multiplier
        if self.combo > 0:
            score_gain = int(score_gain * (1.0 + self.combo * 0.5))

        # T3 merge bonus
        if max_tier >= TIER_MAX:
            score_gain *= 2

        self.score += score_gain

        # Remove non-survivors with particle effects
        for b in group:
            if b is not survivor:
                self.grid[b.row][b.col] = None
                self._spawn_particles(
                    GRID_OX + b.col * CELL + CELL // 2,
                    GRID_OY + b.row * CELL + CELL // 2,
                    COLOR_INTS[b.color],
                    PARTICLE_COUNT,
                )

        survivor.tier = new_tier
        self._merged_blocks.append(survivor)

    def _do_spread(self, blocks: list[Block]) -> None:
        """Spread color from merged blocks to adjacent blocks."""
        for block in blocks:
            # T3 blocks spread to all 8 neighbors; T1/T2 to 4 neighbors
            neighbors: list[tuple[int, int]]
            if block.tier >= TIER_MAX:
                neighbors = [(0, -1), (0, 1), (-1, 0), (1, 0),
                             (-1, -1), (1, -1), (-1, 1), (1, 1)]
            else:
                neighbors = [(0, -1), (0, 1), (-1, 0), (1, 0)]

            for dc, dr in neighbors:
                nc, nr = block.col + dc, block.row + dr
                if not self._in_bounds(nc, nr):
                    continue
                neighbor = self.grid[nr][nc]
                if neighbor is not None and neighbor.color != block.color:
                    neighbor.color = block.color
                    self._spawn_particles(
                        GRID_OX + nc * CELL + CELL // 2,
                        GRID_OY + nr * CELL + CELL // 2,
                        COLOR_INTS[block.color],
                        PARTICLE_COUNT // 2,
                    )

    def _check_win(self) -> bool:
        """Check if all targets are covered by a block of matching color."""
        for target in self.targets:
            block = self.grid[target.row][target.col]
            if block is None:
                return False
            if target.color >= 0 and block.color != target.color:
                return False
        return True

    # ── Particles ──

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn particles at a position."""
        for _ in range(count):
            angle = random.random() * 6.2832  # 2*pi
            speed = random.random() * 2.0 + 0.5
            vx = speed * __import__("math").cos(angle)
            vy = speed * __import__("math").sin(angle)
            life = PARTICLE_LIFE + random.randint(-5, 5)
            self.particles.append(Particle(x, y, vx, vy, max(life, 3), color))

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    # ── Helpers ──

    def _in_bounds(self, col: int, row: int) -> bool:
        """Check if grid coordinates are in bounds."""
        return 0 <= col < COLS and 0 <= row < ROWS

    def _grid_to_pixel(self, col: int, row: int) -> tuple[int, int]:
        """Convert grid coordinates to pixel center."""
        return (
            GRID_OX + col * CELL + CELL // 2,
            GRID_OY + row * CELL + CELL // 2,
        )

    # ── Draw ──

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(0)

        # Grid lines
        self._draw_grid()
        # Targets (under blocks)
        self._draw_targets()
        # Blocks
        self._draw_blocks()
        # Player
        self._draw_player()
        # Particles (on top)
        self._draw_particles()
        # HUD overlay
        self._draw_hud()

        # Phase overlays
        if self.phase == Phase.TITLE:
            self._draw_title_screen()
        elif self.phase == Phase.LEVEL_CLEAR:
            self._draw_level_clear_screen()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over_screen("GAME OVER")
        elif self.phase == Phase.VICTORY:
            self._draw_game_over_screen("VICTORY!")

    def _draw_grid(self) -> None:
        """Draw grid lines."""
        for r in range(ROWS + 1):
            y = GRID_OY + r * CELL
            pyxel.line(GRID_OX, y, GRID_OX + COLS * CELL, y, 5)  # DARK_BLUE
        for c in range(COLS + 1):
            x = GRID_OX + c * CELL
            pyxel.line(x, GRID_OY, x, GRID_OY + ROWS * CELL, 5)

    def _draw_targets(self) -> None:
        """Draw target markers on the grid."""
        for target in self.targets:
            cx = GRID_OX + target.col * CELL + CELL // 2
            cy = GRID_OY + target.row * CELL + CELL // 2
            color = COLOR_INTS[target.color] if target.color >= 0 else 7  # WHITE for any
            # Draw diamond shape
            s = 8
            pyxel.line(cx - s, cy, cx, cy - s, color)
            pyxel.line(cx, cy - s, cx + s, cy, color)
            pyxel.line(cx + s, cy, cx, cy + s, color)
            pyxel.line(cx, cy + s, cx - s, cy, color)
            # If "any" target, add inner cross
            if target.color < 0:
                pyxel.line(cx - 4, cy, cx + 4, cy, 7)
                pyxel.line(cx, cy - 4, cx, cy + 4, 7)

    def _draw_blocks(self) -> None:
        """Draw all blocks on the grid."""
        for r in range(ROWS):
            for c in range(COLS):
                block = self.grid[r][c]
                if block is None:
                    continue
                cx = GRID_OX + c * CELL + CELL // 2
                cy = GRID_OY + r * CELL + CELL // 2
                size = TIER_SIZES[block.tier]
                color = COLOR_INTS[block.color]

                # Draw block fill
                pyxel.rect(cx - size, cy - size, size * 2, size * 2, color)
                # Draw border (brighter for higher tiers)
                border_color = 7 if block.tier >= TIER_MAX else (15 if block.tier == 2 else 13)
                pyxel.rectb(cx - size, cy - size, size * 2, size * 2, border_color)
                # Draw tier indicator (dots)
                if block.tier >= 2:
                    dot_color = 0
                    for i in range(block.tier):
                        dx = (i - (block.tier - 1) / 2) * 4
                        pyxel.pset(int(cx + dx), cy, dot_color)

    def _draw_player(self) -> None:
        """Draw the player on the grid."""
        cx = GRID_OX + self.player_col * CELL + CELL // 2
        cy = GRID_OY + self.player_row * CELL + CELL // 2
        s = 10
        # Player is a bright green bordered square
        pyxel.rect(cx - s, cy - s, s * 2, s * 2, 3)  # GREEN
        pyxel.rectb(cx - s, cy - s, s * 2, s * 2, 7)  # WHITE border
        # Direction indicator (small dot)
        pyxel.pset(cx, cy, 0)

    def _draw_particles(self) -> None:
        """Draw active particles."""
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_hud(self) -> None:
        """Draw HUD overlay with score, level, combo."""
        # Semi-transparent top bar
        pyxel.rect(0, 0, SCREEN_W, 9, 0)
        pyxel.text(2, 1, f"LV{self.level}", 7)
        pyxel.text(50, 1, f"SCORE:{self.score}", 10)
        if self.combo > 1:
            pyxel.text(130, 1, f"COMBO x{self.combo}!", 8)
        pyxel.text(210, 1, f"MV:{self.moves}", 6)

    def _draw_title_screen(self) -> None:
        """Draw title screen overlay."""
        # Darken background
        for y in range(0, SCREEN_H, 2):
            for x in range(0, SCREEN_W, 2):
                c = pyxel.pget(x, y)
                if c != 0:
                    pyxel.pset(x, y, 1)  # NAVY tint

        title_y = 80
        pyxel.text(SCREEN_W // 2 - 40, title_y, "CHAIN PUSH", 7)
        pyxel.text(SCREEN_W // 2 - 52, title_y + 12, "Sokoban x Synthesis", 6)

        # Blinking start prompt
        if (self._title_frame // TITLE_BLINK) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 40, title_y + 40, "PRESS SPACE", 10)

        pyxel.text(SCREEN_W // 2 - 50, title_y + 56, "Arrow/WASD: Move", 13)
        pyxel.text(SCREEN_W // 2 - 52, title_y + 66, "Push blocks to MERGE", 5)
        pyxel.text(SCREEN_W // 2 - 58, title_y + 76, "Same-color chains SPREAD!", 11)
        pyxel.text(SCREEN_W // 2 - 32, title_y + 90, "R: Restart", 15)

    def _draw_level_clear_screen(self) -> None:
        """Draw level clear overlay."""
        pyxel.text(SCREEN_W // 2 - 36, SCREEN_H // 2 - 4, "LEVEL CLEAR!", 10)
        if self.max_combo > 1:
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 10,
                       f"Max Combo: x{self.max_combo}", 11)

    def _draw_game_over_screen(self, title: str) -> None:
        """Draw game over / victory overlay."""
        # Darken
        for y in range(0, SCREEN_H, 3):
            pyxel.line(0, y, SCREEN_W, y, 1)

        pyxel.text(SCREEN_W // 2 - 24, SCREEN_H // 2 - 20, title, 8 if "OVER" in title else 11)
        pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 4, f"Score: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 52, SCREEN_H // 2 + 16,
                   f"Max Combo: x{self.max_combo}", 10)
        pyxel.text(SCREEN_W // 2 - 52, SCREEN_H // 2 + 36,
                   "Press R to restart", 15)


if __name__ == "__main__":
    Game()
