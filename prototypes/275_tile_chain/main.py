"""275_tile_chain — Mahjong solitaire tile-matching with COMBO chain mechanics.

Core fun moment: 狙った色の牌を連続で取り続けてCOMBOが加速し、
SUPER MATCH突入で一気に盤面を崩す瞬間が面白い。
"""
from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
COLS = 12
ROWS = 8
CELL = 20
GRID_X = 40
GRID_Y = 16
LAYER_OFFSET = 3
TILE_SIZE = 18
TOTAL_LAYERS = 3
TIMER_FRAMES = 5400  # 90s * 60fps
SUPER_DURATION = 300  # 5s
DESELECT_TIME = 120  # 2s
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15.0
HEAT_CAP = 100.0

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

TILE_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW_COLORS: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

# Layer definitions: (col_start, col_end_exclusive, row_start, row_end_exclusive, tiles_per_color)
LAYER_DEFS: tuple[tuple[int, int, int, int, int], ...] = (
    (0, 12, 0, 8, 24),   # Layer 0: full 12x8 = 96, 24 per color
    (1, 11, 1, 7, 15),   # Layer 1: 10x6 = 60, 15 per color
    (2, 10, 2, 6, 8),    # Layer 2: 8x4 = 32, 8 per color
)


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(enum.IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Tile:
    col: int
    row: int
    layer: int
    color: int
    alive: bool = True
    exposed: bool = False
    selected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 1


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="TILE CHAIN", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.tiles: list[Tile] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.time_left: int = TIMER_FRAMES
        self.selected_tile: Tile | None = None
        self.deselect_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.last_matched_color: int = -1
        self._shake_frames: int = 0

    # ── Tile Initialization ─────────────────────────────────────────

    def _init_tiles(self) -> None:
        """Create the layered pyramid of colored tiles."""
        self.tiles = []
        for layer_idx, (c0, c1, r0, r1, per_color) in enumerate(LAYER_DEFS):
            colors_pool: list[int] = []
            for c in TILE_COLORS:
                colors_pool.extend([c] * per_color)
            self._rng.shuffle(colors_pool)
            idx = 0
            for row in range(r0, r1):
                for col in range(c0, c1):
                    self.tiles.append(Tile(col=col, row=row, layer=layer_idx, color=colors_pool[idx]))
                    idx += 1
        self._update_exposed()

    # ── Exposure / Coverage ─────────────────────────────────────────

    def _find_tile_at(self, col: int, row: int, layer: int) -> Tile | None:
        """Find an alive tile at the given grid position and layer."""
        for t in self.tiles:
            if t.col == col and t.row == row and t.layer == layer and t.alive:
                return t
        return None

    def _is_covered(self, tile: Tile) -> bool:
        """Check if this tile is covered by any alive tile in the layer above."""
        if tile.layer >= TOTAL_LAYERS - 1:
            return False
        above = self._find_tile_at(tile.col, tile.row, tile.layer + 1)
        return above is not None and above.alive

    def _update_exposed(self) -> None:
        """Recalculate which tiles are exposed."""
        for t in self.tiles:
            if t.alive:
                t.exposed = not self._is_covered(t)
            else:
                t.exposed = False

    def _exposed_pairs_exist(self) -> bool:
        """Check if any matching exposed pair exists (non-alive tiles are ignored)."""
        exposed_tiles = [t for t in self.tiles if t.alive and t.exposed]
        colors_seen: set[int] = set()
        for t in exposed_tiles:
            if t.color in colors_seen:
                return True
            colors_seen.add(t.color)
        return False

    # ── Pixel / Grid Conversion ─────────────────────────────────────

    def _find_top_tile_at(self, px: int, py: int) -> Tile | None:
        """Find the topmost alive tile at pixel position, from top layer down."""
        for layer in range(TOTAL_LAYERS - 1, -1, -1):
            ox = GRID_X + layer * LAYER_OFFSET
            oy = GRID_Y + layer * LAYER_OFFSET
            col = (px - ox) // CELL
            row = (py - oy) // CELL
            if 0 <= col < COLS and 0 <= row < ROWS:
                tile = self._find_tile_at(col, row, layer)
                if tile is not None and tile.alive:
                    tx = ox + col * CELL + 1
                    ty = oy + row * CELL + 1
                    if tx <= px < tx + TILE_SIZE and ty <= py < ty + TILE_SIZE:
                        return tile
        return None

    # ── Click Handling ──────────────────────────────────────────────

    def _handle_click(self, col: int, row: int) -> None:
        """Process a tile click at the given grid position.

        This method receives grid coordinates converted from pixel space.
        It's separate from pyxel input for testability.
        """
        tile = self._find_top_tile_at(
            GRID_X + col * CELL + CELL // 2,
            GRID_Y + row * CELL + CELL // 2,
        )
        if tile is None:
            return

        if not tile.alive or not tile.exposed:
            return

        if self.selected_tile is None:
            # First selection
            tile.selected = True
            self.selected_tile = tile
            self.deselect_timer = DESELECT_TIME
            return

        # Already have a selection
        if tile is self.selected_tile:
            # Click same tile: deselect
            self.selected_tile.selected = False
            self.selected_tile = None
            self.deselect_timer = 0
            return

        # Check match
        is_super = self.super_timer > 0
        same_color = tile.color == self.selected_tile.color

        if same_color or is_super:
            self._match_tiles(self.selected_tile, tile)
        else:
            self._handle_mismatch(self.selected_tile, tile)

        self.selected_tile.selected = False
        self.selected_tile = None
        self.deselect_timer = 0

    # ── Match / Mismatch Logic ──────────────────────────────────────

    def _match_tiles(self, t1: Tile, t2: Tile) -> None:
        """Remove matched pair, update score/combo."""
        t1.alive = False
        t2.alive = False

        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.last_matched_color = t1.color

        base_score = 100 * self.combo
        super_mult = 3 if self.super_timer > 0 else 1
        earned = base_score * super_mult
        self.score += earned

        # Spawn effects
        cx1, cy1 = self._tile_center(t1)
        cx2, cy2 = self._tile_center(t2)
        if self.super_timer > 0:
            self._spawn_super_particles(cx1, cy1)
            self._spawn_super_particles(cx2, cy2)
        else:
            self._spawn_match_particles(cx1, cy1, t1.color)
            self._spawn_match_particles(cx2, cy2, t2.color)

        label = f"+{earned}"
        fcolor = PINK if self.super_timer > 0 else LIME
        self.floating_texts.append(FloatingText(
            (cx1 + cx2) / 2, (cy1 + cy2) / 2, label, 30, fcolor,
        ))
        if self.combo >= 4 and self.super_timer == 0:
            self.super_timer = SUPER_DURATION
            self.floating_texts.append(FloatingText(
                cx1, cy1 - 12, "SUPER MATCH!", 60, PINK,
            ))
        elif self.combo >= 2:
            self.floating_texts.append(FloatingText(
                cx1, cy1 - 12, f"COMBO x{self.combo}", 30, YELLOW,
            ))

        # Update exposure after removal
        self._update_exposed()

    def _handle_mismatch(self, t1: Tile, t2: Tile) -> None:
        """Handle wrong-color second click."""
        self.combo = 0
        t1.selected = False
        t2.selected = False
        self._update_heat(HEAT_MISMATCH)
        self._shake_frames = 6
        self.last_matched_color = -1

        cx1, cy1 = self._tile_center(t1)
        cx2, cy2 = self._tile_center(t2)
        self._spawn_wrong_particles(cx1, cy1)
        self._spawn_wrong_particles(cx2, cy2)
        self.floating_texts.append(FloatingText(
            (cx1 + cx2) / 2, (cy1 + cy2) / 2, "WRONG!", 30, RED,
        ))

    # ── Tile Coordinate Helper ──────────────────────────────────────

    def _tile_center(self, tile: Tile) -> tuple[float, float]:
        """Return the pixel center of a tile."""
        ox = GRID_X + tile.layer * LAYER_OFFSET
        oy = GRID_Y + tile.layer * LAYER_OFFSET
        return (
            ox + tile.col * CELL + CELL / 2,
            oy + tile.row * CELL + CELL / 2,
        )

    # ── Heat System ─────────────────────────────────────────────────

    def _update_heat(self, delta: float) -> None:
        """Add heat (clamped to [0, HEAT_CAP])."""
        self.heat = min(max(self.heat + delta, 0.0), HEAT_CAP)

    def _decay_heat(self) -> None:
        """Frame-based heat decay."""
        self._update_heat(-HEAT_DECAY)

    # ── Particle Systems ────────────────────────────────────────────

    def _spawn_match_particles(self, x: float, y: float, color: int) -> None:
        """Spawn 8 particles for a normal match."""
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=10 + self._rng.randint(0, 10),
                color=color,
                size=1 + self._rng.randint(0, 1),
            ))

    def _spawn_super_particles(self, x: float, y: float) -> None:
        """Spawn 12 rainbow-colored particles for SUPER MATCH."""
        for _ in range(12):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15 + self._rng.randint(0, 10),
                color=self._rng.choice(RAINBOW_COLORS),
                size=1 + self._rng.randint(0, 1),
            ))

    def _spawn_wrong_particles(self, x: float, y: float) -> None:
        """Spawn 4 red particles for wrong click."""
        for _ in range(4):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.3, 1.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=8 + self._rng.randint(0, 4),
                color=RED,
            ))

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._init_state()
            self._init_tiles()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.time_left -= 1
        self._decay_heat()

        if self.super_timer > 0:
            self.super_timer -= 1

        if self.deselect_timer > 0:
            self.deselect_timer -= 1
            if self.deselect_timer <= 0 and self.selected_tile is not None:
                self.selected_tile.selected = False
                self.selected_tile = None

        # Update effects
        self._update_particles()
        self._update_floating_texts()

        # Shake decay
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # Game over checks
        alive_count = sum(1 for t in self.tiles if t.alive)
        if alive_count == 0:
            self.score += (self.time_left // 60) * 10
            self.phase = Phase.GAME_OVER
            return
        if self.time_left <= 0:
            self.phase = Phase.GAME_OVER
            return
        if self.heat >= HEAT_CAP:
            self.phase = Phase.GAME_OVER
            return
        if not self._exposed_pairs_exist():
            self.phase = Phase.GAME_OVER
            return

        # Mouse click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._init_state()
            self._init_tiles()
            self.phase = Phase.PLAYING
        elif pyxel.btnp(pyxel.KEY_ESCAPE):
            self._init_state()
            self.phase = Phase.TITLE

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self._shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 36, 50, "TILE CHAIN", WHITE)

        lines = [
            ("Match same-color tiles!", WHITE),
            ("Click pairs to clear pyramid", WHITE),
            ("", WHITE),
            ("Same-color combos build chain", LIME),
            ("COMBO x4 = SUPER MATCH!", YELLOW),
            ("  (any pair matches, 3x score)", YELLOW),
            ("Wrong color = HEAT + 15", ORANGE),
            ("HEAT 100 = GAME OVER", RED),
            ("", WHITE),
            ("90 seconds to clear the pyramid", GRAY),
            ("", WHITE),
            ("SPACE / ENTER to start", WHITE),
        ]
        y = 80
        for text, color in lines:
            if text:
                pyxel.text(SCREEN_W // 2 - len(text) * 4 // 2, y, text, color)
            y += 14

        # Decorations: sample colored tiles
        for i, col in enumerate(TILE_COLORS):
            tx = 60 + i * 56
            ty = 30
            pyxel.rect(tx, ty, 18, 18, col)
            pyxel.rectb(tx, ty, 18, 18, WHITE)

    def _draw_playing(self) -> None:
        self._draw_tiles()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_tiles(self) -> None:
        """Draw all tiles layer by layer (bottom first)."""
        alive_tiles = [t for t in self.tiles if t.alive]
        if not alive_tiles:
            return
        # Sort by layer for correct draw order
        sorted_tiles = sorted(alive_tiles, key=lambda t: t.layer)
        for tile in sorted_tiles:
            ox = GRID_X + tile.layer * LAYER_OFFSET
            oy = GRID_Y + tile.layer * LAYER_OFFSET
            x = ox + tile.col * CELL + 1
            y = oy + tile.row * CELL + 1

            # SUPER MATCH pulse effect
            if self.super_timer > 0 and tile.exposed:
                pulse = (pyxel.frame_count // 8) % len(RAINBOW_COLORS)
                border_color = RAINBOW_COLORS[pulse]
            else:
                border_color = WHITE

            if tile.selected:
                # Selected tile: CYAN border
                pyxel.rect(x - 1, y - 1, TILE_SIZE + 2, TILE_SIZE + 2, CYAN)
                pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, tile.color)
            else:
                # Normal tile
                pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, tile.color)
                pyxel.rectb(x, y, TILE_SIZE, TILE_SIZE, border_color)

                # Dimmed effect for covered tiles
                if not tile.exposed:
                    for ly in range(y + 1, y + TILE_SIZE, 3):
                        pyxel.line(x + 1, ly, x + TILE_SIZE - 2, ly, BLACK)

    def _draw_hud(self) -> None:
        # Top bar
        pyxel.rect(0, 0, SCREEN_W, 15, NAVY)
        pyxel.line(0, 15, SCREEN_W, 15, DARK_BLUE)

        pyxel.text(2, 3, f"SCORE:{self.score:05d}", WHITE)

        seconds = max(0, self.time_left // 60)
        timer_color = WHITE if seconds > 20 else (YELLOW if seconds > 10 else RED)
        pyxel.text(80, 3, f"TIME:{seconds:02d}", timer_color)

        combo_color = WHITE
        if self.combo >= 4:
            combo_color = PINK
        elif self.combo >= 2:
            combo_color = YELLOW
        elif self.combo >= 1:
            combo_color = LIME
        pyxel.text(146, 3, f"COMBO:{self.combo}", combo_color)

        # Heat bar
        pyxel.text(SCREEN_W - 84, 3, "HEAT", GRAY)
        bar_x = SCREEN_W - 54
        heat_pct = min(self.heat / HEAT_CAP, 1.0)
        heat_color = RED if self.heat > 70 else (ORANGE if self.heat > 30 else YELLOW)
        pyxel.rect(bar_x, 4, 50, 8, BLACK)
        pyxel.rect(bar_x, 4, int(50 * heat_pct), 8, heat_color)
        pyxel.rectb(bar_x, 4, 50, 8, GRAY)

        # SUPER MATCH indicator
        if self.super_timer > 0:
            pulse = (pyxel.frame_count // 10) % 2
            color = PINK if pulse else YELLOW
            super_text = f"SUPER MATCH! {self.super_timer // 60}s"
            tw = len(super_text) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H - 20, super_text, color)

        # Combo info at bottom
        if self.selected_tile is not None:
            sel_text = "Selected — click matching tile"
            pyxel.text(SCREEN_W // 2 - len(sel_text) * 4 // 2, SCREEN_H - 10, sel_text, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.size == 1:
                pyxel.pset(int(p.x), int(p.y), p.color)
            else:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = min(ft.life / 30, 1.0)
            col = ft.color if alpha > 0.3 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

    def _draw_game_over(self) -> None:
        # Draw dim tiles in background
        alive_tiles = [t for t in self.tiles if t.alive]
        if alive_tiles:
            sorted_tiles = sorted(alive_tiles, key=lambda t: t.layer)
            for tile in sorted_tiles:
                ox = GRID_X + tile.layer * LAYER_OFFSET
                oy = GRID_Y + tile.layer * LAYER_OFFSET
                x = ox + tile.col * CELL + 1
                y = oy + tile.row * CELL + 1
                pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, tile.color)
                pyxel.rectb(x, y, TILE_SIZE, TILE_SIZE, DARK_BLUE)

        # Panel
        px = SCREEN_W // 2 - 90
        py_coord = SCREEN_H // 2 - 60
        pyxel.rect(px, py_coord, 180, 120, NAVY)
        pyxel.rectb(px, py_coord, 180, 120, WHITE)

        alive_count = sum(1 for t in self.tiles if t.alive)
        if alive_count == 0:
            title = "ALL CLEAR!"
            title_c = LIME
        elif self.heat >= HEAT_CAP:
            title = "MELTDOWN!"
            title_c = RED
        elif self.time_left <= 0:
            title = "TIME UP!"
            title_c = ORANGE
        else:
            title = "GAME OVER"
            title_c = RED

        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, py_coord + 10, title, title_c)
        pyxel.text(SCREEN_W // 2 - 60, py_coord + 30, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, py_coord + 44, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, py_coord + 58, f"TILES LEFT: {alive_count}", GRAY)
        if alive_count == 0:
            pyxel.text(SCREEN_W // 2 - 60, py_coord + 72, "+TIME BONUS!", LIME)
        pyxel.text(SCREEN_W // 2 - 50, py_coord + 90, "SPACE to Retry", WHITE)
        pyxel.text(SCREEN_W // 2 - 45, py_coord + 102, "ESC for Title", GRAY)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
