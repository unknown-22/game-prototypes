"""BELT CHAIN — Conveyor Belt Factory Puzzle Prototype.

Core fun moment: changing machine color to match incoming items, building
COMBO chain from consecutive same-color processing, then triggering
SUPER CHARGE (rainbow mode, 3x score, auto-match everything).
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
FPS = 60
ITEM_SIZE = 16
INITIAL_ITEM_SPEED = 1.5
LANE_Y = [52, 100, 148]
PROCESS_X = 190
MACHINE_LANE = 1
SPAWN_INTERVAL_BASE = 60
SPAWN_INTERVAL_MIN = 25
GAME_TIME = 60 * FPS
SUPER_DURATION = 300
SUPER_COMBO_THRESHOLD = 4
SUPER_SCORE_MULTIPLIER = 3
HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_MISS = 5.0
HEAT_DECAY = 0.02
SPAWN_MARGIN = -ITEM_SIZE
MAX_ITEMS = 15

# Pyxel palette colors (raw ints)
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

COLORS = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_NAMES = ["RED", "LIME", "DBLUE", "YELLOW"]
RAINBOW = [RED, ORANGE, YELLOW, LIME, CYAN, PINK]

# Button layout
BTN_Y = 210
BTN_W = 50
BTN_H = 22
BTN_GAP = 10
BTN_START_X = (SCREEN_W - (4 * BTN_W + 3 * BTN_GAP)) // 2
BTN_X = [BTN_START_X + i * (BTN_W + BTN_GAP) for i in range(4)]

LANE_HEIGHT = 48


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BeltItem:
    lane: int
    x: float
    color: int
    processed: bool = False
    alive: bool = True


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
    phase: Phase
    score: int
    best_score: int
    combo: int
    max_combo: int
    heat: float
    game_timer: int
    super_timer: int
    frame: int
    machine_color: int
    machine_index: int
    items: list[BeltItem]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    spawn_timer: int
    processed_count: int
    shake_frames: int
    belt_offset: float
    belt_dot_timer: int
    item_speed: float
    _rng: random.Random

    def __new__(cls) -> Game:  # type: ignore[misc]
        obj = object.__new__(cls)
        obj.phase = Phase.TITLE
        obj.score = 0
        obj.best_score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.heat = 0.0
        obj.game_timer = GAME_TIME
        obj.super_timer = 0
        obj.frame = 0
        obj.machine_color = COLORS[0]
        obj.machine_index = 0
        obj.items = []
        obj.particles = []
        obj.floating_texts = []
        obj.spawn_timer = 0
        obj.processed_count = 0
        obj.shake_frames = 0
        obj.belt_offset = 0.0
        obj.belt_dot_timer = 0
        obj.item_speed = INITIAL_ITEM_SPEED
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="BELT CHAIN", fps=FPS, display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = GAME_TIME
        self.super_timer = 0
        self.frame = 0
        self.machine_color = COLORS[0]
        self.machine_index = 0
        self.items.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.spawn_timer = 0
        self.processed_count = 0
        self.shake_frames = 0
        self.belt_offset = 0.0
        self.belt_dot_timer = 0
        self.item_speed = INITIAL_ITEM_SPEED

    # ------------------------------------------------------------------
    # Update dispatch
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            self._update_title()
        elif self.phase is Phase.PLAYING:
            self._update_playing()
        elif self.phase is Phase.GAME_OVER:
            self._update_game_over()

    # ------------------------------------------------------------------
    # Title update
    # ------------------------------------------------------------------

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self._start_game()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.game_timer = GAME_TIME
        self.spawn_timer = SPAWN_INTERVAL_BASE

    # ------------------------------------------------------------------
    # Playing update
    # ------------------------------------------------------------------

    def _update_playing(self) -> None:
        self.frame += 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self._end_game()
            return

        if self.heat >= HEAT_MAX:
            self._end_game()
            return

        self._update_super_timer()
        self._update_escalation()
        self._update_items()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.heat >= HEAT_MAX:
            self._end_game()
            return

        # Spawning
        if len(self.items) < MAX_ITEMS:
            if self._update_spawn_timer():
                self.spawn_timer = self._get_spawn_interval()
                item = self._spawn_item()
                if item:
                    self.items.append(item)

        # Multi-spawn for difficulty
        elapsed = GAME_TIME - self.game_timer
        if elapsed >= 30 * FPS and len(self.items) < MAX_ITEMS - 1:
            pass
        if elapsed >= 45 * FPS:
            pass

        self._handle_input()

        # Belt animation
        self.belt_offset = (self.belt_offset + self.item_speed * 0.3) % 8
        self.belt_dot_timer = (self.belt_dot_timer + 1) % 12

    # ------------------------------------------------------------------
    # Game over update
    # ------------------------------------------------------------------

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R):
            self.reset()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        self.shake_frames = 10
        if self.score > self.best_score:
            self.best_score = self.score

    # ------------------------------------------------------------------
    # Testable logic methods
    # ------------------------------------------------------------------

    def _spawn_item(self) -> BeltItem | None:
        if len(self.items) >= MAX_ITEMS:
            return None
        lane = self._rng.randint(0, 2)
        color = self._rng.choice(COLORS)
        return BeltItem(
            lane=lane,
            x=float(SPAWN_MARGIN),
            color=color,
        )

    def _update_items(self) -> None:
        for item in self.items:
            item.x += self.item_speed

        for item in self.items:
            if not item.processed and PROCESS_X - ITEM_SIZE <= item.x <= PROCESS_X + ITEM_SIZE:
                score_gain, heat_gain, is_match = self._process_item(item)
                self.score += score_gain
                self.heat += heat_gain
                if is_match:
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.processed_count += 1
                    iy = LANE_Y[item.lane]
                    self._spawn_match_particles(item)
                    self._spawn_floating_text(
                        item.x, iy - 8,
                        f"+{score_gain}", WHITE, 30,
                    )
                    if self.combo >= 2:
                        self._spawn_floating_text(
                            item.x, iy - 20,
                            f"CMB x{self.combo}", YELLOW, 40,
                        )
                    self._update_combo()
                else:
                    self.combo = 0
                    iy = LANE_Y[item.lane]
                    self._spawn_mismatch_particles(item)
                    self._spawn_floating_text(
                        item.x, iy - 8,
                        "WRONG!", RED, 20,
                    )

        # Mark processed items past the zone for removal
        for item in self.items:
            if item.processed and item.x > PROCESS_X + ITEM_SIZE * 3:
                item.alive = False

        self.items = [it for it in self.items if it.alive and it.x <= SCREEN_W + ITEM_SIZE]

    def _process_item(self, item: BeltItem) -> tuple[int, float, bool]:
        item.processed = True
        if self.super_timer > 0:
            return 10 * SUPER_SCORE_MULTIPLIER, 0.0, True
        if item.color == self.machine_color:
            score = 10 * self.combo if self.combo > 0 else 10
            return score, 0.0, True
        return 0, HEAT_MISMATCH, False

    def _update_combo(self) -> None:
        if self.combo >= SUPER_COMBO_THRESHOLD and self.super_timer == 0:
            self.super_timer = SUPER_DURATION
            self.shake_frames = 6
            self._spawn_super_burst()
            self._spawn_floating_text(
                SCREEN_W // 2 - 36, SCREEN_H // 2 - 10,
                "SUPER CHARGE!", PINK, 60,
            )

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        self.heat = min(HEAT_MAX, self.heat)

    def _update_spawn_timer(self) -> bool:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            return True
        return False

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _get_spawn_interval(self) -> int:
        elapsed = GAME_TIME - self.game_timer
        t = elapsed / GAME_TIME
        return int(SPAWN_INTERVAL_BASE - t * (SPAWN_INTERVAL_BASE - SPAWN_INTERVAL_MIN))

    def _update_escalation(self) -> None:
        elapsed = GAME_TIME - self.game_timer
        t = elapsed / GAME_TIME
        self.item_speed = INITIAL_ITEM_SPEED + t * 1.5

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _handle_input(self) -> None:
        # Keyboard
        if pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_Q):
            self._set_machine_color(0)
        if pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_W):
            self._set_machine_color(1)
        if pyxel.btnp(pyxel.KEY_3) or pyxel.btnp(pyxel.KEY_E):
            self._set_machine_color(2)
        if pyxel.btnp(pyxel.KEY_4) or pyxel.btnp(pyxel.KEY_R):
            self._set_machine_color(3)

        # Mouse wheel
        if pyxel.mouse_wheel != 0:
            self.machine_index = (self.machine_index + pyxel.mouse_wheel) % 4
            self.machine_color = COLORS[self.machine_index]

        # Mouse click on buttons
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            for i in range(4):
                bx = BTN_X[i]
                by = BTN_Y
                if bx <= mx <= bx + BTN_W and by <= my <= by + BTN_H:
                    self._set_machine_color(i)
                    break

    def _set_machine_color(self, index: int) -> None:
        self.machine_index = index
        self.machine_color = COLORS[index]

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_match_particles(self, item: BeltItem) -> None:
        iy = LANE_Y[item.lane]
        count = 12 if self.super_timer > 0 else 6
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.5)
            self.particles.append(Particle(
                x=item.x, y=iy + ITEM_SIZE // 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15, color=item.color,
            ))

    def _spawn_mismatch_particles(self, item: BeltItem) -> None:
        iy = LANE_Y[item.lane]
        for _ in range(3):
            angle = self._rng.uniform(math.pi, math.pi * 1.8)
            speed = self._rng.uniform(0.8, 2.0)
            self.particles.append(Particle(
                x=item.x, y=iy + ITEM_SIZE // 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=10, color=RED,
            ))

    def _spawn_super_burst(self) -> None:
        for _ in range(12):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(2.0, 5.0)
            self.particles.append(Particle(
                x=SCREEN_W // 2, y=SCREEN_H // 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=20, color=YELLOW,
            ))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Floating texts
    # ------------------------------------------------------------------

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Draw dispatch
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        sx = 0
        sy = 0
        if self.shake_frames > 0:
            intensity = max(1, self.shake_frames // 3)
            sx = self._rng.randint(-intensity, intensity)
            sy = self._rng.randint(-intensity, intensity)

        if self.phase is Phase.TITLE:
            self._draw_background(sx, sy)
            self._draw_title(sx, sy)
        elif self.phase is Phase.PLAYING:
            self._draw_background(sx, sy)
            self._draw_playing(sx, sy)
        elif self.phase is Phase.GAME_OVER:
            self._draw_background(sx, sy)
            self._draw_game_over(sx, sy)

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    def _draw_background(self, sx: int, sy: int) -> None:
        # Factory floor
        for y in range(24, SCREEN_H):
            col = DARK_BLUE if y < 40 else (BROWN if y < 48 else NAVY)
            pyxel.pset(0 + sx, y + sy, col)
        pyxel.rect(0 + sx, 48 + sy, SCREEN_W, SCREEN_H - 48, NAVY)

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title(self, sx: int, sy: int) -> None:
        cx = SCREEN_W // 2 + sx

        pyxel.text(cx - 28, 30 + sy, "BELT CHAIN", YELLOW)
        pyxel.text(cx - 32, 42 + sy, "Factory Puzzle", LIME)

        # Mini belt illustration
        self._draw_mini_belt(cx, 66 + sy)

        pyxel.text(cx - 68, 100 + sy, "Items flow on 3 conveyor lanes.", LIME)
        pyxel.text(cx - 72, 112 + sy, "Match machine color to process!", CYAN)
        pyxel.text(cx - 62, 126 + sy, "COMBO x4 = SUPER CHARGE", YELLOW)
        pyxel.text(cx - 58, 138 + sy, "(rainbow, 3x score!)", PINK)
        pyxel.text(cx - 56, 152 + sy, "Mismatch = HEAT + combo reset", RED)
        pyxel.text(cx - 48, 164 + sy, "HEAT=100 = Game Over", ORANGE)

        pyxel.text(cx - 68, 180 + sy, "1/2/3/4 or Q/W/E/R: switch color", GRAY)
        pyxel.text(cx - 62, 192 + sy, "Click buttons or mouse wheel", GRAY)

        if self.best_score > 0:
            pyxel.text(cx - 40, 208 + sy, f"BEST: {self.best_score}", PINK)

        pyxel.text(cx - 48, 228 + sy, "SPACE/ENTER to START", WHITE)

    def _draw_mini_belt(self, cx: int, y: int) -> None:
        for lane in range(3):
            ly = y + lane * 14
            for i in range(8):
                dot = (i * 8 + int(self.frame * 0.5)) % 64 - 32
                pyxel.pset(cx + dot, ly, GRAY)
            pyxel.line(cx - 32, ly, cx + 32, ly, DARK_BLUE)

    # ------------------------------------------------------------------
    # Playing screen
    # ------------------------------------------------------------------

    def _draw_playing(self, sx: int, sy: int) -> None:
        # Conveyor lanes
        for lane in range(3):
            ly = LANE_Y[lane] + ITEM_SIZE + sy
            self._draw_conveyor(lane, ly, sx, sy)

        # Processing zone line
        px = PROCESS_X + sx
        zone_alpha = (self.frame // 6) % 2
        if zone_alpha:
            pyxel.line(px, LANE_Y[0] + sy, px, LANE_Y[2] + ITEM_SIZE + sy, YELLOW)
        pyxel.rect(px - 1, 28 + sy, 3, SCREEN_H - 28, DARK_BLUE)

        # Items
        for item in self.items:
            self._draw_item(item, sx, sy)

        # Machine indicator
        self._draw_machine(sx, sy)

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x) + sx, int(p.y) + sy, p.color)

        # Floating texts
        for ft in self.floating_texts:
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x - tw // 2) + sx, int(ft.y) + sy, ft.text, ft.color)

        # Color buttons
        self._draw_color_buttons(sx, sy)

        # SUPER border
        if self.super_timer > 0:
            rc = RAINBOW[(self.frame // 4) % len(RAINBOW)]
            pyxel.rectb(sx, sy, SCREEN_W, SCREEN_H, rc)
            pyxel.rectb(sx + 1, sy + 1, SCREEN_W - 2, SCREEN_H - 2, rc)

        # HUD
        self._draw_hud()

        # Mouse cursor
        pyxel.pset(pyxel.mouse_x, pyxel.mouse_y, WHITE)

    def _draw_conveyor(self, lane: int, ly: int, sx: int, sy: int) -> None:
        # Belt lines
        pyxel.line(0 + sx, ly - ITEM_SIZE + sy, SCREEN_W + sx, ly - ITEM_SIZE + sy, DARK_BLUE)
        pyxel.line(0 + sx, ly + sy, SCREEN_W + sx, ly + sy, DARK_BLUE)

        # Animated belt dots
        dot_spacing = 8
        dot_offset = int(self.belt_offset) % dot_spacing
        for x in range(-dot_spacing, SCREEN_W + dot_spacing, dot_spacing):
            dx = x + dot_offset + sx
            lane_indicator = (lane - 1) * 2 + sy
            if 0 <= dx <= SCREEN_W + sx:
                pyxel.pset(dx, ly - ITEM_SIZE // 2 + lane_indicator % 2, GRAY)

    def _draw_item(self, item: BeltItem, sx: int, sy: int) -> None:
        ix = int(item.x) + sx
        iy = LANE_Y[item.lane] + sy

        # Item square with border
        pyxel.rect(ix, iy, ITEM_SIZE, ITEM_SIZE, item.color)
        border_color = GRAY if item.processed else WHITE
        pyxel.rectb(ix - 1, iy - 1, ITEM_SIZE + 2, ITEM_SIZE + 2, border_color)

        # Processed items have a check mark overlay
        if item.processed and self.frame % 8 < 4:
            pyxel.rectb(ix, iy, ITEM_SIZE, ITEM_SIZE, WHITE)

    def _draw_machine(self, sx: int, sy: int) -> None:
        mx = PROCESS_X + sx
        my = LANE_Y[MACHINE_LANE] + sy

        if self.super_timer > 0:
            rc = RAINBOW[(self.frame // 3) % len(RAINBOW)]
            color = rc
        else:
            color = self.machine_color

        # Machine body
        pyxel.rect(mx - 8, my - 4, 16, ITEM_SIZE + 8, color)
        pyxel.rectb(mx - 8, my - 4, 16, ITEM_SIZE + 8, WHITE)

        # Processing arm/indicator
        for lane in range(3):
            if lane == MACHINE_LANE:
                continue
            lx = mx
            ly = LANE_Y[lane] + ITEM_SIZE // 2 + sy
            pyxel.line(mx, my + ITEM_SIZE // 2, lx, ly, color)

        # SUPER glow
        if self.super_timer > 0:
            glow_r = 12 if self.frame % 10 < 5 else 10
            pyxel.circb(mx, my + ITEM_SIZE // 2, glow_r, YELLOW)

    def _draw_color_buttons(self, sx: int, sy: int) -> None:
        by = BTN_Y + sy
        for i in range(4):
            bx = BTN_X[i] + sx
            is_selected = (i == self.machine_index)

            # Button background
            bg = COLORS[i] if is_selected else BLACK
            pyxel.rect(bx, by, BTN_W, BTN_H, bg)
            pyxel.rectb(bx, by, BTN_W, BTN_H, COLORS[i])
            if is_selected:
                pyxel.rectb(bx + 1, by + 1, BTN_W - 2, BTN_H - 2, WHITE)

            # Label
            label = COLOR_NAMES[i]
            tw = len(label) * 4
            tx = bx + (BTN_W - tw) // 2
            ty = by + (BTN_H - 6) // 2
            tc = BLACK if is_selected and COLORS[i] != DARK_BLUE else WHITE
            pyxel.text(tx, ty, label, tc)

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 18, BLACK)
        pyxel.line(0, 18, SCREEN_W, 18, DARK_BLUE)

        secs = max(0, self.game_timer // FPS)
        tc = RED if secs <= 10 else WHITE
        pyxel.text(2, 2, f"SCORE:{self.score}", WHITE)

        combo_color = RED if self.combo >= SUPER_COMBO_THRESHOLD else (YELLOW if self.combo >= 2 else GRAY)
        pyxel.text(100, 2, f"CMB:x{self.combo}", combo_color)

        pyxel.text(180, 2, f"TIME:{secs}", tc)

        if self.super_timer > 0:
            ss = self.super_timer // FPS
            pyxel.text(248, 2, f"SUPER:{ss}", PINK)

        pyxel.text(2, 10, f"HEAT:{int(self.heat)}", WHITE)

        # Heat bar
        hx = 50
        hy = 11
        hw = SCREEN_W - hx - 2
        hh = 5
        pyxel.rect(hx, hy, hw, hh, NAVY)
        heat_fill = int(hw * self.heat / HEAT_MAX)
        if heat_fill > 0:
            heat_color = RED if self.heat > 60 else (ORANGE if self.heat > 30 else YELLOW)
            pyxel.rect(hx, hy, heat_fill, hh, heat_color)
        pyxel.rectb(hx - 1, hy - 1, hw + 2, hh + 2, WHITE)

        # Machine color indicator in HUD
        pyxel.rect(310, 10, 8, 6, self.machine_color)

    # ------------------------------------------------------------------
    # Game over screen
    # ------------------------------------------------------------------

    def _draw_game_over(self, sx: int, sy: int) -> None:
        # Overlay
        pyxel.rect(20 + sx, 40 + sy, SCREEN_W - 40, 160 + sy - sy, BLACK)
        pyxel.rectb(20 + sx, 40 + sy, SCREEN_W - 40, 160, WHITE)

        cx = SCREEN_W // 2 + sx

        pyxel.text(cx - 28, 50 + sy, "GAME OVER", RED)

        if self.heat >= HEAT_MAX:
            pyxel.text(cx - 40, 66 + sy, "OVERHEATED!", ORANGE)
        elif self.game_timer <= 0:
            pyxel.text(cx - 28, 66 + sy, "TIME'S UP!", YELLOW)

        pyxel.text(cx - 36, 84 + sy, f"SCORE: {self.score}", WHITE)
        pyxel.text(cx - 44, 100 + sy, f"MAX COMBO: x{self.max_combo}", PINK)
        pyxel.text(cx - 46, 116 + sy, f"PROCESSED: {self.processed_count}", LIME)
        pyxel.text(cx - 34, 132 + sy, f"HEAT: {int(self.heat)}%", ORANGE)

        if self.score >= self.best_score and self.best_score > 0:
            pyxel.text(cx - 24, 150 + sy, "NEW BEST!", YELLOW)
        pyxel.text(cx - 34, 166 + sy, f"BEST: {self.best_score}", WHITE)

        pyxel.text(cx - 48, 186 + sy, "SPACE/ENTER to RETRY", WHITE)

        # Mouse cursor
        pyxel.pset(pyxel.mouse_x, pyxel.mouse_y, WHITE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    Game()
