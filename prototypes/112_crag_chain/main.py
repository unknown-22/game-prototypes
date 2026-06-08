"""CRAG CHAIN — Color-match rock climbing. Same-color hold chains build COMBO; COMBO>=4 triggers SUPER REACH (5s, 3x score). Risk: longer reaches cost more stamina."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# ── Color constants (raw pyxel ints) ──────────────────────────────────────
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

HOLD_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
RAINBOW_COLORS: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]

# ── Grid / game constants ────────────────────────────────────────────────
COLS = 8
TOTAL_ROWS = 20
CELL = 24
GRID_X = (320 - COLS * CELL) // 2  # 64
INITIAL_PLAYER_COL = 4
INITIAL_PLAYER_ROW = 11
MAX_REACH_DIST = 2
STAMINA_COST_NEAR = 5
STAMINA_COST_FAR = 12
INITIAL_STAMINA = 100.0
COMBO_FOR_SUPER = 4
SUPER_DURATION = 300  # 5 seconds at 60fps
SUPER_SCORE_MULT = 3
SUPER_STAMINA_MULT = 0.5
HOLDS_PER_ROW_MIN = 2
HOLDS_PER_ROW_MAX = 4
PLAYER_TARGET_SCREEN_Y = 170.0
SCROLL_LERP = 0.12


# ── Phase enum ───────────────────────────────────────────────────────────
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Data classes ─────────────────────────────────────────────────────────
@dataclass
class Hold:
    col: int
    row: int
    color: int  # index into HOLD_COLORS (0-3)
    grabbed: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


# ── Game logic (testable, no pyxel input calls) ──────────────────────────
@dataclass
class Game:
    SCREEN_W: int = 320
    SCREEN_H: int = 240
    COLS: int = COLS
    CELL: int = CELL
    GRID_X: int = GRID_X
    SUPER_DURATION: int = SUPER_DURATION
    INITIAL_STAMINA: float = INITIAL_STAMINA
    COMBO_FOR_SUPER: int = COMBO_FOR_SUPER

    # State (all pre-init for headless Game.__new__)
    phase: Phase = Phase.TITLE
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    stamina: float = INITIAL_STAMINA
    max_stamina: float = INITIAL_STAMINA
    combo_color: int = -1  # -1 = no combo active
    player_col: int = INITIAL_PLAYER_COL
    player_row: int = INITIAL_PLAYER_ROW
    scroll_offset: float = 0.0
    total_height: int = 0
    super_reach_timer: int = 0
    holds: list[Hold] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    game_timer: int = 0
    shake_frames: int = 0
    highest_generated_row: int = 0  # lowest row number generated (can be negative)
    lowest_generated_row: int = TOTAL_ROWS - 1
    last_score_popup: tuple[str, float, float, int] | None = None  # text, x, y, life
    _rng: random.Random = field(default_factory=random.Random)

    # ── Initialization ───────────────────────────────────────────────────

    def _init_state(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.stamina = self.INITIAL_STAMINA
        self.combo_color = -1
        self.player_col = INITIAL_PLAYER_COL
        self.player_row = INITIAL_PLAYER_ROW
        self.scroll_offset = float(self.player_row * self.CELL - PLAYER_TARGET_SCREEN_Y)
        self.total_height = 0
        self.super_reach_timer = 0
        self.holds.clear()
        self.particles.clear()
        self.game_timer = 0
        self.shake_frames = 0
        self.highest_generated_row = 0
        self.lowest_generated_row = TOTAL_ROWS - 1
        self.last_score_popup = None
        self._generate_holds(0, TOTAL_ROWS - 1)
        self._ensure_start_hold()

    def _ensure_start_hold(self) -> None:
        start = self._get_hold(INITIAL_PLAYER_COL, INITIAL_PLAYER_ROW)
        if start is None:
            start = Hold(col=INITIAL_PLAYER_COL, row=INITIAL_PLAYER_ROW, color=1)  # GREEN
            self.holds.append(start)
        else:
            start.color = 1
        start.grabbed = True
        self.combo_color = 1
        self.combo = 1

    # ── Hold generation ──────────────────────────────────────────────────

    def _generate_holds(self, start_row: int, end_row: int) -> None:
        for row in range(start_row, end_row + 1):
            if self._get_hold(0, row) is not None and self._get_hold(0, row) is not None:
                # Check if row already has holds (simple check: is there any hold in this row?)
                has_holds = any(h.row == row for h in self.holds)
                if has_holds:
                    continue
            count = self._rng.randint(HOLDS_PER_ROW_MIN, HOLDS_PER_ROW_MAX)
            cols: set[int] = set()
            while len(cols) < count:
                cols.add(self._rng.randint(0, self.COLS - 1))
            for col in cols:
                color_idx = self._rng.randint(0, len(HOLD_COLORS) - 1)
                self.holds.append(Hold(col=col, row=row, color=color_idx))
        if start_row < self.highest_generated_row:
            self.highest_generated_row = start_row
        if end_row > self.lowest_generated_row:
            self.lowest_generated_row = end_row

    def _get_hold(self, col: int, row: int) -> Hold | None:
        for h in self.holds:
            if h.col == col and h.row == row:
                return h
        return None

    # ── Distance / cost helpers ──────────────────────────────────────────

    @staticmethod
    def _manhattan_dist(col1: int, row1: int, col2: int, row2: int) -> int:
        return abs(col1 - col2) + abs(row1 - row2)

    def _is_adjacent(self, col: int, row: int) -> bool:
        return self._manhattan_dist(self.player_col, self.player_row, col, row) <= MAX_REACH_DIST

    @staticmethod
    def _cost_for_distance(dist: int) -> float:
        if dist <= 1:
            return float(STAMINA_COST_NEAR)
        return float(STAMINA_COST_FAR)

    # ── Grab logic ───────────────────────────────────────────────────────

    def _grab_hold(self, hold: Hold) -> int:
        """Player grabs a hold. Returns score gained."""
        if hold.grabbed:
            return 0
        if not self._is_adjacent(hold.col, hold.row):
            return 0

        is_super = self.super_reach_timer > 0
        dist = self._manhattan_dist(self.player_col, self.player_row, hold.col, hold.row)

        cost = self._cost_for_distance(dist)
        if is_super:
            cost *= SUPER_STAMINA_MULT
        self.stamina = max(0.0, self.stamina - cost)

        row_diff = max(0, self.player_row - hold.row)
        if hold.row < self.player_row:
            self.total_height += row_diff

        self.player_col = hold.col
        self.player_row = hold.row
        hold.grabbed = True

        if is_super:
            self.combo += 1
        elif self.combo_color == -1 or self.combo_color == hold.color:
            self.combo += 1
            self.combo_color = hold.color
        else:
            self.combo = 1
            self.combo_color = hold.color

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        cx = float(self.GRID_X + hold.col * self.CELL + self.CELL // 2)
        cy = float(hold.row * self.CELL + self.CELL // 2)
        self._spawn_particles(cx, cy, HOLD_COLORS[hold.color], 6)

        activated_super = False
        if self.combo >= self.COMBO_FOR_SUPER and self.super_reach_timer == 0:
            self.super_reach_timer = self.SUPER_DURATION
            self.shake_frames = 10
            self._spawn_particles(cx, cy, YELLOW, 25)
            activated_super = True

        mult = self.combo
        if is_super:
            mult = int(mult * SUPER_SCORE_MULT)
        grab_score = (row_diff * 10 + 10) * mult
        self.score += grab_score

        if activated_super:
            self.last_score_popup = (
                f"SUPER REACH! x{SUPER_SCORE_MULT}",
                cx,
                cy,
                60,
            )
        elif grab_score > 0:
            self.last_score_popup = (
                f"+{grab_score}",
                cx,
                cy,
                30,
            )

        return grab_score

    # ── Scroll / generation ──────────────────────────────────────────────

    def _update_scroll(self) -> None:
        target = float(self.player_row * self.CELL - PLAYER_TARGET_SCREEN_Y)
        self.scroll_offset += (target - self.scroll_offset) * SCROLL_LERP

    def _generate_more_holds_if_needed(self) -> None:
        visible_top_r = self.scroll_offset / self.CELL
        while self.highest_generated_row > visible_top_r - 3:
            new_row = self.highest_generated_row - 1
            if new_row < -80:
                break
            self._generate_holds(new_row, new_row)
            self.highest_generated_row = new_row

    # ── Particles ────────────────────────────────────────────────────────

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    # ── Game over check ──────────────────────────────────────────────────

    def _check_game_over(self) -> bool:
        if self.stamina <= 0.0:
            self.stamina = 0.0
            self.phase = Phase.GAME_OVER
            return True
        visible_top_r = self.scroll_offset / self.CELL
        player_screen_r = self.player_row - visible_top_r
        visible_rows = self.SCREEN_H / self.CELL
        if player_screen_r > visible_rows + 1:
            self.phase = Phase.GAME_OVER
            return True
        return False

    # ── Frame update (testable) ──────────────────────────────────────────

    def update_frame(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        self.game_timer += 1
        if self.super_reach_timer > 0:
            self.super_reach_timer -= 1
            if self.super_reach_timer == 0:
                self.combo = 0
                self.combo_color = -1
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.last_score_popup is not None:
            _, _, _, life = self.last_score_popup
            life -= 1
            if life <= 0:
                self.last_score_popup = None
            else:
                self.last_score_popup = (
                    self.last_score_popup[0],
                    self.last_score_popup[1],
                    self.last_score_popup[2],
                    life,
                )
        self._update_scroll()
        self._generate_more_holds_if_needed()
        self._update_particles()
        self._check_game_over()
        self._ensure_reachable_holds()

    def _ensure_reachable_holds(self) -> None:
        """If no ungrabbed holds within reach, generate one nearby."""
        has_reachable = False
        for h in self.holds:
            if not h.grabbed and self._is_adjacent(h.col, h.row):
                has_reachable = True
                break
        if not has_reachable:
            # Generate a hold adjacent to player
            for dr in range(-MAX_REACH_DIST, MAX_REACH_DIST + 1):
                for dc in range(-MAX_REACH_DIST, MAX_REACH_DIST + 1):
                    nr = self.player_row + dr
                    nc = self.player_col + dc
                    if abs(dr) + abs(dc) > MAX_REACH_DIST or (dr == 0 and dc == 0):
                        continue
                    existing = self._get_hold(nc, nr)
                    if existing is not None and not existing.grabbed:
                        return  # found one
                    if existing is None:
                        color_idx = self._rng.randint(0, len(HOLD_COLORS) - 1)
                        self.holds.append(Hold(col=nc, row=nr, color=color_idx))
                        if nr < self.highest_generated_row:
                            self.highest_generated_row = nr
                        return

    # ── Mouse grab attempt ───────────────────────────────────────────────

    def attempt_grab_at(self, screen_x: float, screen_y: float) -> int | None:
        """Try grab at screen coordinates. Returns score gained or None."""
        if self.phase != Phase.PLAYING:
            return None

        col = int((screen_x - self.GRID_X) / self.CELL)
        row = int((screen_y + self.scroll_offset) / self.CELL)

        if not (0 <= col < self.COLS):
            return None

        hold = self._get_hold(col, row)
        if hold is None or hold.grabbed:
            return None
        if not self._is_adjacent(col, row):
            return None

        score = self._grab_hold(hold)
        self._check_game_over()
        return score

    # ── Reset / factory ──────────────────────────────────────────────────

    def reset_to_title(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.stamina = self.INITIAL_STAMINA
        self.combo_color = -1
        self.player_col = INITIAL_PLAYER_COL
        self.player_row = INITIAL_PLAYER_ROW
        self.scroll_offset = float(self.player_row * self.CELL - PLAYER_TARGET_SCREEN_Y)
        self.total_height = 0
        self.super_reach_timer = 0
        self.holds.clear()
        self.particles.clear()
        self.game_timer = 0
        self.shake_frames = 0
        self.highest_generated_row = 0
        self.lowest_generated_row = TOTAL_ROWS - 1
        self.last_score_popup = None

    @staticmethod
    def _make_game() -> Game:
        g = Game.__new__(Game)
        Game.__init__(g)
        g.reset_to_title()
        return g


# ── Pyxel App ─────────────────────────────────────────────────────────────


class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="CRAG CHAIN", display_scale=2)
        self.game = Game()
        self.game.reset_to_title()
        self._prev_mouse = False
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        g = self.game
        g.update_frame()

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        match g.phase:
            case Phase.TITLE:
                if pyxel.btnp(pyxel.KEY_RETURN):
                    g._init_state()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                if pyxel.btnp(pyxel.KEY_RETURN):
                    g.reset_to_title()

    def _update_playing(self) -> None:
        g = self.game
        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        just_pressed = mouse_pressed and not self._prev_mouse
        self._prev_mouse = mouse_pressed

        if just_pressed:
            mx = float(pyxel.mouse_x)
            my = float(pyxel.mouse_y)
            g.attempt_grab_at(mx, my)

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        g = self.game
        pyxel.cls(BLACK)

        match g.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game()
                self._draw_game_over_overlay()

    def _screen_shake_offset(self) -> tuple[float, float]:
        g = self.game
        if g.shake_frames > 0:
            ox = math.sin(pyxel.frame_count * 1.3) * 3.0
            oy = math.cos(pyxel.frame_count * 1.7) * 3.0
            return ox, oy
        return 0.0, 0.0

    # ── Title screen ─────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        pyxel.text(108, 60, "CRAG CHAIN", WHITE)
        pyxel.text(80, 78, "Click same-color holds for COMBO!", GRAY)
        pyxel.text(88, 90, "COMBO x4 = SUPER REACH!", PINK)
        pyxel.rect(100, 110, 120, 1, GRAY)
        pyxel.text(72, 120, "Reach distance 1: 5 stamina", WHITE)
        pyxel.text(72, 132, "Reach distance 2: 12 stamina", YELLOW)
        pyxel.text(72, 144, "Longer reach = more risk", GRAY)
        pyxel.text(72, 160, "SUPER REACH: 5s, 3x score, half cost", PINK)
        pyxel.text(100, 210, "Press ENTER to start", WHITE)

    # ── Game screen ──────────────────────────────────────────────────────

    def _draw_game(self) -> None:
        ox, oy = self._screen_shake_offset()

        self._draw_grid_lines(ox, oy)
        self._draw_holds(ox, oy)
        self._draw_particles(ox, oy)
        self._draw_player(ox, oy)
        self._draw_hud()
        self._draw_score_popup(ox, oy)
        self._draw_super_reach_indicator()

    def _draw_grid_lines(self, ox: float, oy: float) -> None:
        g = self.game
        # Draw faint column lines
        for col in range(g.COLS + 1):
            x = int(g.GRID_X + col * g.CELL + ox)
            pyxel.line(x, int(oy), x, g.SCREEN_H, GRAY)
        # Draw faint row lines
        visible_top_r = g.scroll_offset / g.CELL
        start_r = int(visible_top_r) - 1
        end_r = start_r + int(g.SCREEN_H / g.CELL) + 3
        for row in range(start_r, end_r):
            y = int(row * g.CELL - g.scroll_offset + oy)
            pyxel.line(int(g.GRID_X + ox), y, int(g.GRID_X + g.COLS * g.CELL + ox), y, GRAY)

    def _draw_holds(self, ox: float, oy: float) -> None:
        g = self.game
        for h in g.holds:
            sx = int(g.GRID_X + h.col * g.CELL + g.CELL // 2 + ox)
            sy = int(h.row * g.CELL + g.CELL // 2 - g.scroll_offset + oy)
            if sy < -16 or sy > g.SCREEN_H + 16:
                continue

            color = HOLD_COLORS[h.color]
            is_adj = g._is_adjacent(h.col, h.row) and not h.grabbed

            if h.grabbed:
                # Dimmed, smaller
                pyxel.circb(sx, sy, 6, GRAY)
            elif not is_adj:
                # Unreachable — dim
                pyxel.circ(sx, sy, 8, GRAY)
                pyxel.circb(sx, sy, 8, GRAY)
            else:
                # Normal reachable hold
                pyxel.circ(sx, sy, 8, color)
                pyxel.circb(sx, sy, 8, WHITE if g.super_reach_timer > 0 else color)

            # Highlight active combo color holds
            if g.super_reach_timer > 0 and is_adj and not h.grabbed:
                alpha = int((math.sin(pyxel.frame_count * 0.2) + 1) * 2)
                if alpha > 0:
                    pyxel.circb(sx, sy, 10, RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)])

    def _draw_particles(self, ox: float, oy: float) -> None:
        g = self.game
        for p in g.particles:
            px = int(p.x + ox)
            py = int(p.y - g.scroll_offset + oy)
            if 0 <= px < g.SCREEN_W and 0 <= py < g.SCREEN_H:
                if p.life > 10:
                    pyxel.circ(px, py, p.size, p.color)
                else:
                    pyxel.pset(px, py, p.color)

    def _draw_player(self, ox: float, oy: float) -> None:
        g = self.game
        cx = int(g.GRID_X + g.player_col * g.CELL + g.CELL // 2 + ox)
        cy = int(g.player_row * g.CELL + g.CELL // 2 - g.scroll_offset + oy)

        # Diamond shape for player
        r = 6
        color = WHITE
        if g.super_reach_timer > 0:
            color = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]

        # Draw diamond: top, right, bottom, left
        pyxel.tri(cx, cy - r, cx - r, cy, cx + r, cy, color)
        pyxel.tri(cx, cy + r, cx - r, cy, cx + r, cy, color)

        # Outer ring for SUPER REACH glow
        if g.super_reach_timer > 0:
            pyxel.circb(cx, cy, r + 3, color)

    def _draw_hud(self) -> None:
        g = self.game

        # Stamina bar (top)
        bar_w = 120
        bar_h = 8
        bar_x = 4
        bar_y = 4
        pct = g.stamina / g.max_stamina
        stamina_color = GREEN if pct > 0.5 else (YELLOW if pct > 0.25 else RED)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        pyxel.rect(bar_x, bar_y, int(bar_w * pct), bar_h, stamina_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + 2, bar_y + 1, f"STAMINA {int(g.stamina)}", BLACK)

        # Score (top right)
        pyxel.text(g.SCREEN_W - 4 - len(f"SCORE {g.score}") * 4, 4, f"SCORE {g.score}", WHITE)

        # Combo (below stamina)
        combo_color = WHITE
        if g.combo >= 4:
            combo_color = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
        elif g.combo >= 2:
            combo_color = YELLOW
        pyxel.text(4, 16, f"COMBO x{g.combo}", combo_color)

        # Height / Max combo
        pyxel.text(4, 26, f"HEIGHT {g.total_height}", WHITE)

    def _draw_score_popup(self, ox: float, oy: float) -> None:
        g = self.game
        if g.last_score_popup is None:
            return
        text, cx, cy, life = g.last_score_popup
        px = int(cx + ox)
        py = int(cy - g.scroll_offset + oy) - 16
        if life > 0:
            color = PINK if "SUPER" in text else YELLOW
            pyxel.text(px - len(text) * 2, py, text, color)

    def _draw_super_reach_indicator(self) -> None:
        g = self.game
        if g.super_reach_timer <= 0:
            return
        # Blinking SUPER REACH text
        if (pyxel.frame_count // 8) % 2 == 0:
            pyxel.text(g.SCREEN_W // 2 - 50, g.SCREEN_H - 12, "SUPER REACH!", PINK)

        # Timer bar at bottom
        bar_w = 100
        bar_h = 4
        bar_x = g.SCREEN_W // 2 - bar_w // 2
        bar_y = g.SCREEN_H - 6
        pct = g.super_reach_timer / g.SUPER_DURATION
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        pyxel.rect(bar_x, bar_y, int(bar_w * pct), bar_h, PINK)

    # ── Game over overlay ────────────────────────────────────────────────

    def _draw_game_over_overlay(self) -> None:
        g = self.game
        pyxel.rect(60, 70, 200, 100, NAVY)
        pyxel.rectb(60, 70, 200, 100, WHITE)

        pyxel.text(85, 82, "GAME OVER — {:.1f}m climbed!".format(g.total_height * 0.5), WHITE)
        pyxel.text(85, 96, f"Score: {g.score}", YELLOW)
        pyxel.text(85, 108, f"Max COMBO: x{g.max_combo}", WHITE)

        # Determine death cause
        if g.stamina <= 0:
            pyxel.text(85, 122, "Cause: Stamina depleted", RED)
        else:
            pyxel.text(85, 122, "Cause: Fell off wall", RED)

        pyxel.text(100, 148, "Press ENTER to retry", WHITE)


if __name__ == "__main__":
    App()
