"""072_pair_chain — Color-Match Concentration Memory Game.

Core fun moment: building COMBO by matching same-color pairs, then at COMBO ≥ 3
triggering a CHAIN REVEAL that propagates to adjacent face-down cards via BFS.
Risk/reward: committing to memory and trying to chain-match for bonus score.
"""
from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
GRID_X = 16
GRID_Y = 24
CELL = 48
COLS = 6
ROWS = 6
SCREEN_W = 320
SCREEN_H = 240
TOTAL_CARDS = COLS * ROWS  # 36
TIMER_SECONDS = 90
TIMER_FRAMES = TIMER_SECONDS * 30
MATCH_ANIM_FRAMES = 20
MISS_ANIM_FRAMES = 30
CHAIN_REVEAL_FRAMES = 30
PARTICLE_COUNT = 8

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

CARD_COLORS: tuple[int, int, int, int] = (RED, GREEN, DARK_BLUE, YELLOW)
PAIRS_PER_COLOR = 4
WILD_PAIRS = 2


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(enum.IntEnum):
    TITLE = 0
    FLIP_FIRST = 1
    FLIP_SECOND = 2
    MATCH_ANIM = 3
    MISS_ANIM = 4
    CHAIN_REVEAL = 5
    GAME_OVER = 6


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Card:
    color: int
    revealed: bool = False
    matched: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Pair Chain", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Initialize or reset all game state."""
        self.phase: Phase = Phase.TITLE
        self._init_state()

    def _init_state(self) -> None:
        self.grid: list[list[Card]] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.pairs_matched: int = 0
        self.timer: int = TIMER_FRAMES
        self.first_card: tuple[int, int] | None = None
        self.second_card: tuple[int, int] | None = None
        self.anim_timer: int = 0
        self.chain_bonus: int = 0
        self.matched_color: int = 0
        self.particles: list[Particle] = []
        self._make_grid()

    # ── Grid Generation ─────────────────────────────────────────────

    def _make_grid(self) -> None:
        """Create shuffled grid of 32 colored cards (4 colors × 4 pairs)
        + 4 wild cards (2 wild pairs)."""
        colors: list[int] = []
        for c in CARD_COLORS:
            colors.extend([c] * (PAIRS_PER_COLOR * 2))
        colors.extend([PEACH] * (WILD_PAIRS * 2))
        self._rng.shuffle(colors)

        self.grid = [[Card(color=0) for _ in range(COLS)] for _ in range(ROWS)]
        idx = 0
        for row in range(ROWS):
            for col in range(COLS):
                self.grid[row][col] = Card(color=colors[idx])
                idx += 1

    # ── Pure Logic: Card Click ──────────────────────────────────────

    def _pixel_to_cell(self, px: int, py: int) -> tuple[int, int] | None:
        """Convert pixel coords to grid (col, row), or None if out of bounds."""
        col = (px - GRID_X) // CELL
        row = (py - GRID_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return col, row
        return None

    def _cell_center(self, col: int, row: int) -> tuple[float, float]:
        """Return pixel center of a grid cell."""
        return (GRID_X + col * CELL + CELL / 2, GRID_Y + row * CELL + CELL / 2)

    def _grid_click(self, col: int, row: int) -> None:
        """Handle a card click at the given grid position."""
        card = self.grid[row][col]
        if card.revealed or card.matched:
            return

        if self.phase == Phase.FLIP_FIRST:
            card.revealed = True
            self.first_card = (col, row)
            self.phase = Phase.FLIP_SECOND

        elif self.phase == Phase.FLIP_SECOND:
            if self.first_card is not None and (col, row) == self.first_card:
                return
            card.revealed = True
            self.second_card = (col, row)
            matched = self._check_match()
            if matched:
                self.anim_timer = MATCH_ANIM_FRAMES
                self.phase = Phase.MATCH_ANIM
            else:
                self.anim_timer = MISS_ANIM_FRAMES
                self.phase = Phase.MISS_ANIM

    def _check_match(self) -> bool:
        """Check if the two currently selected cards match.
        Returns True for match, False for miss. Updates combo, score, pairs_matched."""
        if self.first_card is None or self.second_card is None:
            return False

        c1 = self.grid[self.first_card[1]][self.first_card[0]]
        c2 = self.grid[self.second_card[1]][self.second_card[0]]

        is_wild1 = c1.color == PEACH
        is_wild2 = c2.color == PEACH
        if is_wild1 or is_wild2 or c1.color == c2.color:
            # Match!
            self.combo += 1
            self.score += 100 * self.combo
            self.max_combo = max(self.max_combo, self.combo)
            self.pairs_matched += 1
            self.matched_color = c1.color if not is_wild1 else c2.color
            c1.matched = True
            c2.matched = True

            # Spawn particles at both card centers
            cx1, cy1 = self._cell_center(*self.first_card)
            cx2, cy2 = self._cell_center(*self.second_card)
            self._spawn_particles(cx1, cy1, c1.color, PARTICLE_COUNT)
            self._spawn_particles(cx2, cy2, c2.color, PARTICLE_COUNT)

            return True

        # Miss
        self.combo = 0
        return False

    # ── Pure Logic: Chain Reveal ────────────────────────────────────

    def _trigger_chain_reveal(self) -> int:
        """BFS chain reveal from both matched cards.
        Auto-flips adjacent face-down cards.
        Returns total bonus points earned."""
        if self.first_card is None or self.second_card is None:
            return 0

        # Collect all face-down cards adjacent to the matched pair via BFS
        candidates = self._bfs_adjacent(self.first_card[0], self.first_card[1])
        candidates.update(self._bfs_adjacent(self.second_card[0], self.second_card[1]))

        bonus = 0
        for col, row in candidates:
            card = self.grid[row][col]
            if card.revealed or card.matched:
                continue
            card.revealed = True
            # Check if this card matches the matched color or is wild
            if card.color == self.matched_color or card.color == PEACH or self.matched_color == PEACH:
                card.matched = True
                self.pairs_matched += 1
                bonus += 50
                cx, cy = self._cell_center(col, row)
                self._spawn_particles(cx, cy, card.color, PARTICLE_COUNT // 2)

        self.score += bonus
        self.chain_bonus = bonus
        return bonus

    def _bfs_adjacent(self, col: int, row: int) -> set[tuple[int, int]]:
        """BFS from origin to collect all face-down cards in 4-direction adjacent cells.
        Only traverses through face-down, non-matched cards."""
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = []

        # Seed: collect all 4-direction neighbors of origin
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                card = self.grid[nr][nc]
                if not card.revealed and not card.matched:
                    queue.append((nc, nr))

        # BFS
        while queue:
            cc, cr = queue.pop(0)
            if (cc, cr) in visited:
                continue
            visited.add((cc, cr))
            for dc, dr in directions:
                nc, nr = cc + dc, cr + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if (nc, nr) not in visited:
                        card = self.grid[nr][nc]
                        if not card.revealed and not card.matched:
                            queue.append((nc, nr))

        return visited

    # ── Particles ───────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn `count` particles at (x, y) with the given color."""
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15 + self._rng.randint(0, 10),
                color=color,
            ))

    def _update_particles(self) -> None:
        """Update particle positions and remove dead ones."""
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase in (Phase.FLIP_FIRST, Phase.FLIP_SECOND):
            self._update_playing()
        elif self.phase == Phase.MATCH_ANIM:
            self._update_match_anim()
        elif self.phase == Phase.MISS_ANIM:
            self._update_miss_anim()
        elif self.phase == Phase.CHAIN_REVEAL:
            self._update_chain_reveal()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._init_state()
            self.phase = Phase.FLIP_FIRST

    def _update_playing(self) -> None:
        self.timer -= 1
        self._update_particles()

        # Timer check
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        # All matched check
        if self.pairs_matched * 2 >= TOTAL_CARDS:
            self.score += 500
            self.phase = Phase.GAME_OVER
            return

        # Mouse click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            cell = self._pixel_to_cell(pyxel.mouse_x, pyxel.mouse_y)
            if cell is not None:
                self._grid_click(*cell)

    def _update_match_anim(self) -> None:
        self.timer -= 1
        self._update_particles()

        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.pairs_matched * 2 >= TOTAL_CARDS:
            self.score += 500
            self.phase = Phase.GAME_OVER
            return

        self.anim_timer -= 1
        if self.anim_timer <= 0:
            if self.combo >= 3:
                self.chain_bonus = 0
                self._trigger_chain_reveal()
                self.anim_timer = CHAIN_REVEAL_FRAMES
                self.phase = Phase.CHAIN_REVEAL
            else:
                self.first_card = None
                self.second_card = None
                self.phase = Phase.FLIP_FIRST

    def _update_miss_anim(self) -> None:
        self.timer -= 1
        self._update_particles()

        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self.anim_timer -= 1
        if self.anim_timer <= 0:
            # Flip both cards back face-down
            if self.first_card is not None:
                c1 = self.grid[self.first_card[1]][self.first_card[0]]
                c1.revealed = False
            if self.second_card is not None:
                c2 = self.grid[self.second_card[1]][self.second_card[0]]
                c2.revealed = False
            self.first_card = None
            self.second_card = None
            self.phase = Phase.FLIP_FIRST

    def _update_chain_reveal(self) -> None:
        self.timer -= 1
        self._update_particles()

        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.pairs_matched * 2 >= TOTAL_CARDS:
            self.score += 500
            self.phase = Phase.GAME_OVER
            return

        self.anim_timer -= 1
        if self.anim_timer <= 0:
            self.first_card = None
            self.second_card = None
            self.phase = Phase.FLIP_FIRST

    def _update_game_over(self) -> None:
        self._update_particles()
        if pyxel.btnp(pyxel.KEY_R):
            self._init_state()
            self.phase = Phase.FLIP_FIRST

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.FLIP_FIRST, Phase.FLIP_SECOND,
                            Phase.MATCH_ANIM, Phase.MISS_ANIM, Phase.CHAIN_REVEAL):
            self._draw_grid()
            self._draw_hud()
            self._draw_particles()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 38, 40, "PAIR CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 54, 60, "Color-Match Memory", GRAY)

        lines = [
            ("Click to flip cards", WHITE),
            ("", WHITE),
            ("Match same colors: COMBO!", LIME),
            ("COMBO x3: CHAIN REVEAL!", YELLOW),
            ("WILD cards match any color", PEACH),
            ("", WHITE),
            ("90 seconds to match all pairs", GRAY),
            ("", WHITE),
            ("SPACE / ENTER to start", WHITE),
        ]
        y = 90
        for text, color in lines:
            if text:
                pyxel.text(SCREEN_W // 2 - len(text) * 4 // 2, y, text, color)
            y += 14

    def _draw_grid(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                self._draw_card(col, row)

    def _draw_card(self, col: int, row: int) -> None:
        card = self.grid[row][col]
        x = GRID_X + col * CELL
        y = GRID_Y + row * CELL

        # Card background
        if card.matched:
            # Matched cards: dimmed color
            pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, card.color)
            pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, LIGHT_BLUE)
        elif card.revealed:
            # Revealed face-up
            pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, card.color)
            pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, WHITE)
        else:
            # Face-down
            pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, GRAY)
            pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, DARK_BLUE)

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 22, NAVY)
        pyxel.line(0, 22, SCREEN_W, 22, DARK_BLUE)

        # Score (left)
        score_str = f"SCORE:{self.score:05d}"
        pyxel.text(4, 5, score_str, WHITE)

        # Timer (center)
        seconds = max(0, self.timer // 30)
        t = f"TIME:{seconds:02d}"
        timer_color = WHITE if seconds > 10 else RED
        pyxel.text(SCREEN_W // 2 - 16, 5, t, timer_color)

        # Combo (right)
        combo_str = "COMBO:0" if self.combo == 0 else f"COMBO:x{self.combo}"
        combo_color = WHITE
        if self.combo >= 3:
            combo_color = YELLOW
        elif self.combo >= 1:
            combo_color = LIME
        pyxel.text(SCREEN_W - 58, 5, combo_str, combo_color)

        # Phase-specific info
        if self.phase == Phase.CHAIN_REVEAL and self.chain_bonus > 0:
            chain_text = f"CHAIN! +{self.chain_bonus}"
            pyxel.text(SCREEN_W // 2 - len(chain_text) * 4 // 2, SCREEN_H - 30, chain_text, YELLOW)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_game_over(self) -> None:
        # Background dim
        for row in range(ROWS):
            for col in range(COLS):
                card = self.grid[row][col]
                x = GRID_X + col * CELL
                y = GRID_Y + row * CELL
                if card.matched:
                    pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, card.color)
                    pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, DARK_BLUE)
                else:
                    pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, GRAY)
                    pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, DARK_BLUE)

        # Overlay panel
        px = SCREEN_W // 2 - 90
        py = SCREEN_H // 2 - 60
        pyxel.rect(px, py, 180, 120, NAVY)
        pyxel.rectb(px, py, 180, 120, WHITE)

        # Victory or defeat
        all_cleared = self.pairs_matched * 2 >= TOTAL_CARDS
        if all_cleared:
            title = "ALL CLEAR!"
            title_c = LIME
        else:
            title = "GAME OVER"
            title_c = RED
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, py + 8, title, title_c)

        # Stats
        pyxel.text(SCREEN_W // 2 - 60, py + 30, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 60, py + 44, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, py + 58, f"PAIRS: {self.pairs_matched}/{TOTAL_CARDS // 2}", GRAY)
        if all_cleared:
            pyxel.text(SCREEN_W // 2 - 60, py + 72, "+500 CLEAR BONUS!", LIME)
        pyxel.text(SCREEN_W // 2 - 38, py + 90, "R to Restart", WHITE)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
