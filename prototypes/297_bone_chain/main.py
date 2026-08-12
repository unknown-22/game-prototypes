"""FOSSIL CHAIN — Archeological fossil excavation with COMBO chains and CA dirt spreading.

Reinterpreted from game_idea_factory #1 (Score 32.35):
  "synthesis compression" → same-color COMBO chain → SUPER EXCAVATE + BFS fossil SYNTHESIS
  "CA grid fills up → control" → dirt CA spreads from edges, player must excavate to keep the site clear

Core fun moment: building same-color COMBO to unlock SUPER EXCAVATE rainbow mode,
then watching adjacent fossils cascade-synthesize into MEGA FOSSILS for huge score pops.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
DISPLAY_SCALE = 2
GAME_DURATION = 60  # seconds

# Grid
COLS = 8
ROWS = 7
CELL = 30
OFFSET_X = 40
OFFSET_Y = 30

# Cell states
DIRT = -1
EMPTY = 0

# Fossil colors (Pyxel palette)
RED = 8
LIME = 11
DARK_BLUE = 5
YELLOW_COLOR = 10
BROWN = 4
GRAY = 13
FOSSIL_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW_COLOR)
NUM_COLORS = 4

# Fossil tiers
TIER_BONE = 1
TIER_COMPLETE = 2
TIER_MEGA = 3

# Color cycle
CYCLE_START = 25  # frames
CYCLE_END = 12

# Scoring
BASE_SCORE = 10
SYNTH_SCORE = 100
MEGA_SCORE = 300

# COMBO / SUPER
SUPER_COMBO_THRESHOLD = 4
SUPER_DURATION = 300  # frames
SUPER_MULTIPLIER = 3

# SYNTHESIS
SYNTH_MIN_CLUSTER = 3
ANIM_SYNTH_DURATION = 30  # frames

# CA Dirt
DIRT_INTERVAL_START = 90
DIRT_INTERVAL_END = 40
DIRT_SPREAD_CHANCE = 0.2

# Fossil Spawn
SPAWN_INTERVAL_START = 45
SPAWN_INTERVAL_END = 25
SPAWN_MIN_FOSSILS = 8
SPAWN_MAX_FOSSILS = 16
EXCAVATE_FOSSIL_CHANCE = 0.6

# HEAT
HEAT_MAX = 100
HEAT_MISMATCH = 15
HEAT_COVER = 3
HEAT_DECAY = 0.02  # per frame

# Screen shake
SHAKE_MISMATCH_DURATION = 8
SHAKE_MISMATCH_AMP = 3
SHAKE_MEGA_DURATION = 15
SHAKE_MEGA_AMP = 6

# Particles
PARTICLE_MATCH_COUNT = 8
PARTICLE_SUPER_COUNT = 20
PARTICLE_SYNTH_COUNT = 16
PARTICLE_MEGA_COUNT = 24
PARTICLE_WRONG_COUNT = 4

# ── Enums ──────────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Dataclasses ────────────────────────────────────────────────────────

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


# ── Game Logic ─────────────────────────────────────────────────────────

class Game:
    """Pure game logic — no pyxel calls for testable methods."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="FOSSIL CHAIN", fps=FPS, display_scale=DISPLAY_SCALE)
        self.rng = random.Random()
        self.best_score = 0
        self._init_state()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.synth_anim_timer = 0
        self.synth_cluster: set[tuple[int, int]] = set()
        self.timer = GAME_DURATION * FPS
        self.player_color_idx = 0
        self.color_timer = CYCLE_START
        self.dirt_cooldown = DIRT_INTERVAL_START
        self.spawn_cooldown = SPAWN_INTERVAL_START
        self.last_excavated_color: int | None = None
        self.shake_timer = 0
        self.shake_amplitude = 0

        self._grid: list[list[int]] = [[DIRT for _ in range(COLS)] for _ in range(ROWS)]
        self._tiers: list[list[int]] = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        # Initialize grid: center cells exposed, edges dirt
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                self._grid[r][c] = EMPTY

        # Spawn initial fossils
        for _ in range(SPAWN_MIN_FOSSILS):
            self._spawn_single_fossil()

    def reset(self) -> None:
        best = self.best_score
        self.rng = random.Random()
        self._init_state()
        self.best_score = best

    # ── Core Logic (testable, no pyxel input) ───────────────────────

    def _excavate(self, col: int, row: int) -> tuple[bool, str]:
        """Excavate a dirt cell. Returns (matched, event_type)."""
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return (False, "")
        if self._grid[row][col] != DIRT:
            return (False, "")

        is_super = self.super_timer > 0
        was_super_activated = False
        is_fossil = self.rng.random() < EXCAVATE_FOSSIL_CHANCE

        if not is_fossil:
            self._grid[row][col] = EMPTY
            return (False, "")

        fossil_color_idx = self.rng.randint(0, NUM_COLORS - 1)
        self._grid[row][col] = FOSSIL_COLORS[fossil_color_idx]
        self._tiers[row][col] = TIER_BONE

        # First excavation always matches (no previous color to compare)
        first_excavation = self.last_excavated_color is None
        matched = is_super or first_excavation or (self.last_excavated_color == fossil_color_idx)
        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo >= SUPER_COMBO_THRESHOLD and not is_super:
                self.super_timer = SUPER_DURATION
                was_super_activated = True
            mult = SUPER_MULTIPLIER if (is_super or was_super_activated) else 1.0
            pts = int(BASE_SCORE * self.combo * mult)
            self.score += pts
        else:
            self.combo = 0
            self.heat += HEAT_MISMATCH

        self.last_excavated_color = fossil_color_idx

        if is_super:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr = row + dr
                    nc = col + dc
                    if 0 <= nr < ROWS and 0 <= nc < COLS and self._grid[nr][nc] == DIRT:
                        self._grid[nr][nc] = EMPTY

        if was_super_activated:
            return (matched, "super_activate")
        if matched:
            return (matched, "match")
        return (matched, "mismatch")

    def _bfs_synthesis(self, col: int, row: int, color: int) -> set[tuple[int, int]]:
        """BFS to find connected cluster of same-color same-tier fossils."""
        target = FOSSIL_COLORS[color]
        cluster: set[tuple[int, int]] = set()
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return cluster
        start_tier = self._tiers[row][col]
        if self._grid[row][col] != target or start_tier not in (TIER_BONE, TIER_COMPLETE):
            return cluster

        queue: list[tuple[int, int]] = [(col, row)]
        cluster.add((col, row))
        while queue:
            cc, cr = queue.pop(0)
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = cc + dc, cr + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and (nc, nr) not in cluster:
                    if self._grid[nr][nc] == target and self._tiers[nr][nc] == start_tier:
                        cluster.add((nc, nr))
                        queue.append((nc, nr))
        return cluster

    def _try_synthesis(self, cluster: set[tuple[int, int]]) -> tuple[bool, int]:
        """Attempt synthesis on a cluster. Returns (triggered, bonus_score)."""
        if len(cluster) < SYNTH_MIN_CLUSTER:
            return (False, 0)

        sample_c, sample_r = next(iter(cluster))
        start_tier = self._tiers[sample_r][sample_c]

        if start_tier == TIER_COMPLETE:
            for c, r in cluster:
                self._tiers[r][c] = TIER_MEGA
            bonus = MEGA_SCORE * len(cluster) * max(1, self.combo)
        else:
            for c, r in cluster:
                self._tiers[r][c] = TIER_COMPLETE
            bonus = SYNTH_SCORE * len(cluster) * max(1, self.combo)
            self.synth_anim_timer = ANIM_SYNTH_DURATION
            self.synth_cluster = cluster.copy()

        self.score += bonus
        return (True, bonus)

    def _check_all_synthesis(self) -> int:
        """Check entire grid for synthesis opportunities. Returns total bonus."""
        total_bonus = 0
        visited: set[tuple[int, int]] = set()

        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) in visited:
                    continue
                cell_val = self._grid[r][c]
                if cell_val <= 0:
                    continue
                tier = self._tiers[r][c]
                if tier not in (TIER_BONE, TIER_COMPLETE):
                    continue
                color = FOSSIL_COLORS.index(cell_val)
                cluster = self._bfs_synthesis(c, r, color)
                for cell in cluster:
                    visited.add(cell)
                triggered, bonus = self._try_synthesis(cluster)
                if triggered:
                    total_bonus += bonus
        return total_bonus

    def _spread_dirt(self) -> int:
        """Spread dirt via CA. Returns number of cells dirt spread to."""
        new_dirt: list[tuple[int, int]] = []
        for r in range(ROWS):
            for c in range(COLS):
                if self._grid[r][c] != DIRT:
                    continue
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        if self._grid[nr][nc] != DIRT and self.rng.random() < DIRT_SPREAD_CHANCE:
                            new_dirt.append((nc, nr))

        spread_count = 0
        for nc, nr in new_dirt:
            if self._grid[nr][nc] == DIRT:
                continue
            if self._grid[nr][nc] > 0:
                self.heat += HEAT_COVER
            self._grid[nr][nc] = DIRT
            self._tiers[nr][nc] = 0
            spread_count += 1

        return spread_count

    def _spawn_single_fossil(self) -> bool:
        """Spawn one fossil in a random empty cell. Returns True if spawned."""
        empty_cells = [(c, r) for r in range(ROWS) for c in range(COLS) if self._grid[r][c] == EMPTY]
        if not empty_cells:
            return False
        c, r = self.rng.choice(empty_cells)
        color_idx = self.rng.randint(0, NUM_COLORS - 1)
        self._grid[r][c] = FOSSIL_COLORS[color_idx]
        self._tiers[r][c] = TIER_BONE
        return True

    def _spawn_fossils(self) -> int:
        """Spawn 1-2 fossil fragments in random empty cells. Returns number spawned."""
        visible_fossils = sum(1 for r in range(ROWS) for c in range(COLS) if self._grid[r][c] > 0)
        if visible_fossils >= SPAWN_MAX_FOSSILS:
            return 0

        count = self.rng.randint(1, 2)
        spawned = 0
        for _ in range(count):
            if self._spawn_single_fossil():
                spawned += 1
        return spawned

    def _update_heat(self, delta: float) -> None:
        """Update heat by delta, clamping 0-100 and checking game over."""
        self.heat += delta
        if self.heat < 0:
            self.heat = 0
        if self.heat > HEAT_MAX:
            self.heat = HEAT_MAX

    def _update_timer(self) -> bool:
        """Decrement timer by 1 frame. Returns True if time ran out."""
        self.timer -= 1
        return self.timer <= 0

    def _grid_click_to_cell(self, mx: int, my: int) -> tuple[int, int] | None:
        """Convert mouse coordinates to grid cell. Returns (col, row) or None."""
        if mx < OFFSET_X or my < OFFSET_Y:
            return None
        col = (mx - OFFSET_X) // CELL
        row = (my - OFFSET_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return (col, row)
        return None

    # ── Particle / FX helpers ───────────────────────────────────────

    def _spawn_particles(
        self, col: int, row: int, color: int, count: int, *, upward: bool = True
    ) -> None:
        cx = OFFSET_X + col * CELL + CELL // 2
        cy = OFFSET_Y + row * CELL + CELL // 2
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            if upward:
                vy = -abs(vy) - self.rng.uniform(0.5, 2.0)
            else:
                vy = abs(vy) + self.rng.uniform(0.5, 2.0)
            life = self.rng.randint(8, 20)
            self.particles.append(Particle(cx, cy, vx, vy, color, life, life))

    def _spawn_floating_text(
        self, col: int, row: int, text: str, color: int, life: int = 30
    ) -> None:
        x = OFFSET_X + col * CELL + CELL // 2
        y = OFFSET_Y + row * CELL + CELL // 2
        self.floating_texts.append(FloatingText(float(x), float(y), text, color, life))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.PLAYING
                self.timer = GAME_DURATION * FPS
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase != Phase.PLAYING:
            return

        # Timer
        if self._update_timer():
            self._handle_game_over("TIME'S UP!")
            return

        # HEAT decay and check
        self._update_heat(-HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self._handle_game_over("SITE COLLAPSED!")
            return

        # SUPER timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # Synthesis animation
        if self.synth_anim_timer > 0:
            self.synth_anim_timer -= 1

        # Player color cycle
        if self.super_timer <= 0:
            self.color_timer -= 1
            if self.color_timer <= 0:
                progress = 1.0 - (self.timer / (GAME_DURATION * FPS))
                interval = CYCLE_START + (CYCLE_END - CYCLE_START) * progress
                self.color_timer = max(1, int(interval))
                self.player_color_idx = (self.player_color_idx + 1) % NUM_COLORS

        # Dirt spread
        self.dirt_cooldown -= 1
        if self.dirt_cooldown <= 0:
            self._spread_dirt()
            progress = 1.0 - (self.timer / (GAME_DURATION * FPS))
            self.dirt_cooldown = int(DIRT_INTERVAL_START + (DIRT_INTERVAL_END - DIRT_INTERVAL_START) * progress)
            self.dirt_cooldown = max(1, self.dirt_cooldown)

        # Fossil spawn
        self.spawn_cooldown -= 1
        if self.spawn_cooldown <= 0:
            self._spawn_fossils()
            progress = 1.0 - (self.timer / (GAME_DURATION * FPS))
            self.spawn_cooldown = int(SPAWN_INTERVAL_START + (SPAWN_INTERVAL_END - SPAWN_INTERVAL_START) * progress)
            self.spawn_cooldown = max(1, self.spawn_cooldown)

        # Mouse click → excavate
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            cell = self._grid_click_to_cell(pyxel.mouse_x, pyxel.mouse_y)
            if cell is not None:
                col, row = cell
                self._excavate(col, row)
                while self._check_all_synthesis() > 0:
                    pass

        # Update screen shake
        if self.shake_timer > 0:
            self.shake_timer -= 1

        # Update particles and floating texts
        self._update_particles()
        self._update_floating_texts()

    def _handle_game_over(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
        self._spawn_floating_text(COLS // 2, ROWS // 2, reason, pyxel.COLOR_RED, life=90)

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over_overlay()
            return

        # Screen shake camera offset
        cam_x = 0
        cam_y = 0
        if self.shake_timer > 0:
            cam_x = self.rng.randint(-self.shake_amplitude, self.shake_amplitude)
            cam_y = self.rng.randint(-self.shake_amplitude, self.shake_amplitude)
        pyxel.camera(cam_x, cam_y)

        self._draw_game()

        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        title = "FOSSIL CHAIN"
        tw = len(title) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
        pyxel.text(SCREEN_W // 2 - tw // 2, 70, title, pyxel.COLOR_YELLOW)

        pyxel.text(SCREEN_W // 2 - 55, 110, "Click to Start", pyxel.COLOR_WHITE)

        instructions = [
            "Same-color consecutive digs build COMBO",
            "Wrong color resets COMBO + raises HEAT",
            "COMBO x4 = SUPER EXCAVATE (rainbow mode)",
            "3+ adjacent same-color fossils = SYNTHESIS",
        ]
        for i, line in enumerate(instructions):
            txt_w = len(line) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
            pyxel.text(SCREEN_W // 2 - txt_w // 2, 140 + i * 14, line, pyxel.COLOR_GRAY)

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)
        pyxel.text(SCREEN_W // 2 - 40, 70, "GAME OVER", pyxel.COLOR_RED)

        score_str = f"Score: {self.score}"
        best_str = f"Best: {self.best_score}"
        max_combo_str = f"Max Combo: {self.max_combo}"
        for i, s in enumerate((score_str, best_str, max_combo_str)):
            tw = len(s) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
            pyxel.text(SCREEN_W // 2 - tw // 2, 100 + i * 16, s, pyxel.COLOR_WHITE)

        restart_str = "Click to Retry"
        rw = len(restart_str) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
        pyxel.text(SCREEN_W // 2 - rw // 2, 170, restart_str, pyxel.COLOR_YELLOW)

    def _draw_game(self) -> None:
        # Timer bar (top)
        timer_ratio = self.timer / (GAME_DURATION * FPS)
        bar_w = int(240 * timer_ratio)
        col_timer = pyxel.COLOR_CYAN if timer_ratio > 0.5 else (
            pyxel.COLOR_ORANGE if timer_ratio > 0.25 else pyxel.COLOR_RED
        )
        pyxel.rect(40, 8, bar_w, 8, col_timer)
        pyxel.rectb(40, 8, 240, 8, pyxel.COLOR_GRAY)

        # Score / Combo display
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        if self.combo > 1:
            combo_str = f"COMBO x{self.combo}"
            cw = len(combo_str) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
            pyxel.text(SCREEN_W // 2 - cw // 2, OFFSET_Y - 20, combo_str, pyxel.COLOR_YELLOW)
        if self.super_timer > 0:
            super_str = f"SUPER {self.super_timer // 60}s"
            sw = len(super_str) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
            pyxel.text(SCREEN_W // 2 - sw // 2, OFFSET_Y - 10, super_str, pyxel.COLOR_WHITE)

        # Time display
        secs = max(0, self.timer // FPS)
        time_str = f"{secs}s"
        pyxel.text(SCREEN_W - 40, 4, time_str, pyxel.COLOR_WHITE)

        # Draw grid
        grid_w = COLS * CELL
        grid_h = ROWS * CELL

        # SUPER mode rainbow border
        if self.super_timer > 0:
            hue = (pyxel.frame_count // 4) % NUM_COLORS
            border_colors = FOSSIL_COLORS[hue:] + FOSSIL_COLORS[:hue]
            for i in range(NUM_COLORS):
                pyxel.rectb(OFFSET_X - i, OFFSET_Y - i, grid_w + i * 2, grid_h + i * 2, border_colors[i])

        # Grid cells
        for r in range(ROWS):
            for c in range(COLS):
                cx = OFFSET_X + c * CELL
                cy = OFFSET_Y + r * CELL
                val = self._grid[r][c]
                tier = self._tiers[r][c]

                if val == DIRT:
                    pyxel.rect(cx, cy, CELL, CELL, BROWN)
                    pyxel.rectb(cx, cy, CELL, CELL, pyxel.COLOR_BLACK)
                elif val > 0:
                    pyxel.rect(cx, cy, CELL, CELL, pyxel.COLOR_BLACK)
                    color = val
                    mid_x = cx + CELL // 2
                    mid_y = cy + CELL // 2
                    if tier == TIER_BONE:
                        pyxel.circ(mid_x, mid_y, 8, color)
                    elif tier == TIER_COMPLETE:
                        r_diamond = 9
                        pyxel.tri(mid_x, mid_y - r_diamond, mid_x + r_diamond, mid_y, mid_x, mid_y + r_diamond, color)
                        pyxel.tri(mid_x, mid_y + r_diamond, mid_x - r_diamond, mid_y, mid_x, mid_y - r_diamond, color)
                    elif tier == TIER_MEGA:
                        pulse = (math.sin(pyxel.frame_count * 0.15) + 1) * 0.5
                        r_star = int(7 + pulse * 4)
                        for i in range(8):
                            angle = i * math.pi / 4
                            angle2 = (i + 0.5) * math.pi / 4
                            inner = r_star * 0.4
                            x1 = mid_x + math.cos(angle) * r_star
                            y1 = mid_y + math.sin(angle) * r_star
                            x2 = mid_x + math.cos(angle2) * inner
                            y2 = mid_y + math.sin(angle2) * inner
                            x3 = mid_x + math.cos(angle + 0.03) * r_star
                            y3 = mid_y + math.sin(angle + 0.03) * r_star
                            pyxel.tri(x1, y1, x2, y2, x3, y3, color)
                else:
                    pyxel.rect(cx, cy, CELL, CELL, GRAY)
                    pyxel.rectb(cx, cy, CELL, CELL, pyxel.COLOR_BLACK)

        # Synthesis animation flash
        if self.synth_anim_timer > 0 and self.synth_cluster:
            flash = pyxel.frame_count // 4 % 2 == 0
            if flash:
                for cc, cr in self.synth_cluster:
                    cx = OFFSET_X + cc * CELL
                    cy = OFFSET_Y + cr * CELL
                    pyxel.rectb(cx, cy, CELL, CELL, pyxel.COLOR_YELLOW)

        # Grid border
        pyxel.rectb(OFFSET_X, OFFSET_Y, grid_w, grid_h, pyxel.COLOR_WHITE)

        # Player color indicator (bottom-left of grid)
        ind_x = OFFSET_X
        ind_y = OFFSET_Y + ROWS * CELL + 8
        ind_size = 16
        player_color = FOSSIL_COLORS[self.player_color_idx]
        pyxel.rect(ind_x, ind_y, ind_size, ind_size, player_color)
        pyxel.rectb(ind_x, ind_y, ind_size, ind_size, pyxel.COLOR_WHITE)
        pyxel.text(ind_x + ind_size + 4, ind_y + 3, "YOUR COLOR", pyxel.COLOR_WHITE)

        # HEAT bar (right side, vertical)
        heat_bar_x = OFFSET_X + grid_w + 10
        heat_bar_y = OFFSET_Y
        heat_bar_w = 16
        heat_bar_h = grid_h
        heat_ratio = self.heat / HEAT_MAX
        heat_fill = int(heat_bar_h * heat_ratio)
        heat_col = pyxel.COLOR_GREEN if heat_ratio < 0.5 else (
            pyxel.COLOR_YELLOW if heat_ratio < 0.75 else pyxel.COLOR_RED
        )
        pyxel.rect(heat_bar_x, heat_bar_y + heat_bar_h - heat_fill, heat_bar_w, heat_fill, heat_col)
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, pyxel.COLOR_WHITE)
        pyxel.text(heat_bar_x, heat_bar_y - 10, "HEAT", pyxel.COLOR_GRAY)

        # Draw particles
        for p in self.particles:
            alpha = p.life / p.max_life
            if alpha > 0.5:
                pyxel.pset(int(p.x), int(p.y), p.color)
            elif alpha > 0.2:
                pyxel.pset(int(p.x), int(p.y), pyxel.COLOR_GRAY)

        # Draw floating texts
        for ft in self.floating_texts:
            if ft.life > 0:
                alpha = ft.life / 30
                col = ft.color if alpha > 0.3 else pyxel.COLOR_GRAY
                tw = len(ft.text) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
                pyxel.text(int(ft.x - tw // 2), int(ft.y), ft.text, col)

        # Timer label
        pyxel.text(4, 12, "TIME", pyxel.COLOR_GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
