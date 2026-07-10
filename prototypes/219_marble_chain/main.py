from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import ClassVar

import pyxel

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

MARBLE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]

SCREEN_W = 320
SCREEN_H = 240

LANE_X: dict[int, float] = {0: 80.0, 1: 160.0, 2: 240.0}

SWITCH1_Y = 80.0
SWITCH2_Y = 150.0
SWITCH_RECT_W = 20
SWITCH_RECT_H = 10

SWITCH1_RECT = (150, 75, SWITCH_RECT_W, SWITCH_RECT_H)
SWITCH2_RECT = (150, 145, SWITCH_RECT_W, SWITCH_RECT_H)

MARBLE_SPEED = 2.0
MARBLE_RADIUS = 6
LANE_CHANGE_SPEED = 4.0

COLLECTION_Y = 220.0
HUD_H = 16

SPAWN_INTERVAL_INIT = 45
SPAWN_INTERVAL_DECREASE = 3
SPAWN_DECREASE_PERIOD_FRAMES = 15 * 30

HEAT_PER_MISMATCH = 15.0
HEAT_DECAY = 0.03
HEAT_MAX = 100.0

COMBO_FOR_SUPER = 4
SUPER_DURATION = 180
SUPER_SCORE_MULT = 3

GAME_DURATION = 1800
BASE_SCORE = 10

SWITCH_FLASH_FRAMES = 3


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Marble:
    x: float
    y: float
    color: int
    lane: int
    collected: bool = False
    target_x: float = 160.0
    passed_switch1: bool = False
    passed_switch2: bool = False


@dataclass
class Switch:
    rect_x: int
    rect_y: int
    state: int = 1
    from_lane: int = 1
    to_lane: int = 0
    flash_timer: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class BinState:
    last_color: int = -1
    combo: int = 0


class Game:
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        if Game._initialized:
            return
        Game._initialized = True

        pyxel.init(SCREEN_W, SCREEN_H, title="Marble Chain", display_scale=2)
        self._rng = random.Random()
        self._pre_init_state()
        try:
            pyxel.load(str(Path(__file__).with_name("k8x12.bdf")))
        except Exception:
            pass
        pyxel.run(self._update, self._draw)

    def _pre_init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.timer: int = GAME_DURATION
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.super_flash: int = 0
        self.spawn_timer: int = SPAWN_INTERVAL_INIT
        self.spawn_interval: int = SPAWN_INTERVAL_INIT
        self.marbles: list[Marble] = []
        self.switches: list[Switch] = []
        self.bins: list[BinState] = []
        self.particles: list[Particle] = []
        self.score_popups: list[tuple[float, float, int, int, int]] = []
        self.frame: int = 0
        self._init_switches()
        self._init_bins()

    def _init_switches(self) -> None:
        self.switches = [
            Switch(rect_x=150, rect_y=75, state=1, from_lane=1, to_lane=0),
            Switch(rect_x=150, rect_y=145, state=1, from_lane=1, to_lane=2),
        ]

    def _init_bins(self) -> None:
        self.bins = [BinState() for _ in range(3)]

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = GAME_DURATION
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.super_flash = 0
        self.spawn_timer = SPAWN_INTERVAL_INIT
        self.spawn_interval = SPAWN_INTERVAL_INIT
        self.marbles.clear()
        self._init_switches()
        self._init_bins()
        self.particles.clear()
        self.score_popups.clear()

    # --- Update ---

    def _update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    def _update_game_over(self) -> None:
        self._update_heat()
        self._update_particles()
        self._update_score_popups()
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self.timer -= 1
        if self._check_game_over():
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER
            return

        self._update_heat()
        self._update_super_mode()
        self._update_particles()
        self._update_score_popups()
        self._update_switch_flash()
        self._update_marbles()
        self._update_spawning()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

    def _update_spawning(self) -> None:
        elapsed = GAME_DURATION - self.timer
        periods = elapsed // SPAWN_DECREASE_PERIOD_FRAMES
        self.spawn_interval = max(15, SPAWN_INTERVAL_INIT - periods * SPAWN_INTERVAL_DECREASE)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            self.marbles.append(self._spawn_marble())

    def _update_switch_flash(self) -> None:
        for sw in self.switches:
            if sw.flash_timer > 0:
                sw.flash_timer -= 1

    # --- Spawn ---

    def _spawn_marble(self) -> Marble:
        color = self._rng.choice(MARBLE_COLORS)
        return Marble(x=160.0, y=float(HUD_H), color=color, lane=1, target_x=160.0)

    # --- Marbles ---

    def _update_marbles(self) -> None:
        to_collect: list[tuple[Marble, int]] = []

        for m in self.marbles:
            if m.collected:
                continue

            prev_y = m.y
            m.y += MARBLE_SPEED

            if abs(m.x - m.target_x) > 0.1:
                if m.x < m.target_x:
                    m.x = min(m.target_x, m.x + LANE_CHANGE_SPEED)
                else:
                    m.x = max(m.target_x, m.x - LANE_CHANGE_SPEED)

            if m.lane == 1:
                if not m.passed_switch1 and prev_y < SWITCH1_Y <= m.y:
                    m.passed_switch1 = True
                    if self.switches[0].state == 0:
                        m.lane = self.switches[0].to_lane
                        m.target_x = LANE_X[m.lane]

                if not m.passed_switch2 and prev_y < SWITCH2_Y <= m.y:
                    m.passed_switch2 = True
                    if self.switches[1].state == 0:
                        m.lane = self.switches[1].to_lane
                        m.target_x = LANE_X[m.lane]

            if m.y >= COLLECTION_Y and not m.collected:
                to_collect.append((m, m.lane))

        for m, bin_idx in to_collect:
            self._collect_marble(m, bin_idx)

        self.marbles = [m for m in self.marbles if not m.collected]

    # --- Collection ---

    def _collect_marble(self, m: Marble, bin_idx: int) -> None:
        bin_state = self.bins[bin_idx]
        m.collected = True

        if self.super_mode:
            self.combo += 1
            mult = self._compute_combo_multiplier(self.combo)
            score_gain = int(BASE_SCORE * mult * SUPER_SCORE_MULT)
            self.score += score_gain
            bin_state.combo += 1
            bin_state.last_color = m.color
        elif bin_state.last_color == m.color or bin_state.last_color == -1:
            self.combo += 1
            mult = self._compute_combo_multiplier(self.combo)
            score_gain = int(BASE_SCORE * mult)
            self.score += score_gain
            bin_state.combo += 1
            bin_state.last_color = m.color
        else:
            if bin_state.last_color != -1:
                self.heat += HEAT_PER_MISMATCH
                if self.heat > HEAT_MAX:
                    self.heat = HEAT_MAX
            self.combo = 1
            mult = self._compute_combo_multiplier(self.combo)
            score_gain = int(BASE_SCORE * mult)
            self.score += score_gain
            bin_state.combo = 1
            bin_state.last_color = m.color

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= COMBO_FOR_SUPER and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self.super_flash = 0

        self._spawn_collect_particles(m.x, m.y, m.color, 6)
        self.score_popups.append((m.x, m.y, score_gain, 25, m.color))

        if self.combo > 1 and not self.super_mode:
            combo_color = GREEN if self.combo >= 4 else WHITE
            self.score_popups.append((m.x, m.y - 10, 0, 25, combo_color))

    def _compute_combo_multiplier(self, combo: int) -> int:
        if combo < 2:
            return 1
        if combo < 4:
            return 2
        if combo < 6:
            return 3
        return 5

    def _check_game_over(self) -> bool:
        return self.timer <= 0 or self.heat >= HEAT_MAX

    # --- Switch ---

    def _toggle_switch(self, idx: int) -> None:
        sw = self.switches[idx]
        sw.state = 1 - sw.state
        sw.flash_timer = SWITCH_FLASH_FRAMES

    def _handle_click(self, x: int, y: int) -> None:
        rx, ry, rw, rh = SWITCH1_RECT
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            self._toggle_switch(0)
            return

        rx, ry, rw, rh = SWITCH2_RECT
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            self._toggle_switch(1)

    # --- Heat ---

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat -= HEAT_DECAY
            if self.heat < 0:
                self.heat = 0.0

    # --- Super Mode ---

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            self.super_flash = (self.super_flash + 1) % (4 * 8)
            if self.super_timer == 0:
                self.super_mode = False
                self.super_flash = 0
            self._spawn_super_edge_particles()

    def _spawn_super_edge_particles(self) -> None:
        if self.frame % 4 != 0:
            return
        edge = self._rng.randint(0, 3)
        if edge == 0:
            x = float(self._rng.randint(0, SCREEN_W))
            y = 0.0
        elif edge == 1:
            x = float(self._rng.randint(0, SCREEN_W))
            y = float(SCREEN_H)
        elif edge == 2:
            x = 0.0
            y = float(self._rng.randint(0, SCREEN_H))
        else:
            x = float(SCREEN_W)
            y = float(self._rng.randint(0, SCREEN_H))

        self.particles.append(
            Particle(
                x=x,
                y=y,
                vx=self._rng.uniform(-0.5, 0.5),
                vy=self._rng.uniform(-0.5, 0.5),
                life=self._rng.randint(15, 30),
                color=self._rng.choice(MARBLE_COLORS),
            )
        )

    # --- Particles ---

    def _spawn_collect_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-2.5, -0.5),
                    life=self._rng.randint(10, 20),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Score Popups ---

    def _update_score_popups(self) -> None:
        for i in range(len(self.score_popups)):
            x, y, val, life, color = self.score_popups[i]
            y -= 0.5
            life -= 1
            self.score_popups[i] = (x, y, val, life, color)
        self.score_popups = [sp for sp in self.score_popups if sp[3] > 0]

    # --- Draw ---

    def _draw(self) -> None:
        pyxel.cls(DARK_BLUE)

        self._draw_lane_bg()

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_lanes()
        self._draw_switches()
        self._draw_marbles()
        self._draw_particles()
        self._draw_score_popups()
        self._draw_hud()

        if self.super_mode:
            self._draw_super_mode()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_lane_bg(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, HUD_H, NAVY)
        pyxel.rect(0, HUD_H, SCREEN_W, SCREEN_H - HUD_H, BLACK)

        for x in (160, 80, 240):
            for y in range(HUD_H, SCREEN_H, 16):
                col = GRAY if (y // 16) % 2 == 0 else DARK_BLUE
                pyxel.pset(x, y, col)

    def _draw_lanes(self) -> None:
        for x in (80, 160, 240):
            pyxel.line(x, HUD_H, x, SCREEN_H, GRAY)

        for y_pos, label in [(SWITCH1_Y, "L"), (SWITCH2_Y, "R")]:
            for x in (80, 160, 240):
                pyxel.circ(int(x), int(y_pos), 2, WHITE)

    def _draw_switches(self) -> None:
        for sw in self.switches:
            color = GREEN if sw.state == 1 else RED
            if sw.flash_timer > 0:
                color = WHITE
            pyxel.rect(sw.rect_x, sw.rect_y, SWITCH_RECT_W, SWITCH_RECT_H, color)
            pyxel.rectb(sw.rect_x, sw.rect_y, SWITCH_RECT_W, SWITCH_RECT_H, WHITE)

            arrow_x = sw.rect_x + SWITCH_RECT_W // 2
            if sw.state == 1:
                pyxel.line(arrow_x, sw.rect_y - 4, arrow_x, sw.rect_y, WHITE)
            else:
                target_lane_x = int(LANE_X[sw.to_lane])
                if target_lane_x < arrow_x:
                    pyxel.line(arrow_x + 10, sw.rect_y - 4, arrow_x, sw.rect_y, WHITE)
                else:
                    pyxel.line(arrow_x - 10, sw.rect_y - 4, arrow_x, sw.rect_y, WHITE)

    def _draw_marbles(self) -> None:
        for m in self.marbles:
            if m.collected:
                continue
            color = m.color
            if self.super_mode:
                color = self._super_marble_color()
            pyxel.circ(int(m.x), int(m.y), MARBLE_RADIUS, color)
            pyxel.circb(int(m.x), int(m.y), MARBLE_RADIUS, BLACK)
            pyxel.pset(int(m.x) - 2, int(m.y) - 2, WHITE)

    def _super_marble_color(self) -> int:
        idx = (self.super_flash // 8) % len(MARBLE_COLORS)
        return MARBLE_COLORS[idx]

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.15:
                s = 2
                pyxel.rect(int(p.x), int(p.y), s, s, p.color)

    def _draw_score_popups(self) -> None:
        for x, y, val, life, color in self.score_popups:
            alpha = life / 25.0
            if alpha < 0.1:
                continue
            if val > 0:
                text = f"+{val}"
                if self.super_mode:
                    text += " S"
                pyxel.text(int(x) - len(text) * 4, int(y), text, color)
            else:
                combo_text = f"COMBO x{self.combo}!"
                pyxel.text(int(x) - len(combo_text) * 4, int(y), combo_text, color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, HUD_H, NAVY)
        pyxel.line(0, HUD_H, SCREEN_W, HUD_H, GRAY)

        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        timer_sec = max(0, self.timer // 30)
        timer_str = f"TIME:{timer_sec}"
        pyxel.text(SCREEN_W // 2 - len(timer_str) * 4, 2, timer_str, WHITE)

        combo_str = f"COMBO:{self.combo}"
        combo_color = YELLOW if self.combo >= COMBO_FOR_SUPER else (GREEN if self.combo >= 3 else WHITE)
        pyxel.text(SCREEN_W - 10 - len(combo_str) * 8, 2, combo_str, combo_color)

        bar_x = 4
        bar_y = 14
        bar_w = 100
        bar_h = 2
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        fill_color = GREEN
        if self.heat > 60:
            fill_color = ORANGE
        if self.heat > 80:
            fill_color = RED
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, fill_color)

    def _draw_super_mode(self) -> None:
        color_idx = (self.super_flash // 8) % len(MARBLE_COLORS)
        border_color = MARBLE_COLORS[color_idx]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, border_color)

        super_sec = self.super_timer / 30.0
        super_str = f"SUPER! {super_sec:.1f}s"
        pyxel.text(SCREEN_W // 2 - len(super_str) * 4, HUD_H + 4, super_str, YELLOW)

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 50, "MARBLE CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 32, 66, "------------", GRAY)

        pyxel.text(SCREEN_W // 2 - 72, 90, "Route colored marbles into bins", WHITE)
        pyxel.text(SCREEN_W // 2 - 72, 102, "Same color = COMBO chain", GREEN)
        pyxel.text(SCREEN_W // 2 - 72, 114, "Different color = HEAT!", RED)
        pyxel.text(SCREEN_W // 2 - 72, 126, "COMBO x4 = SUPER MODE (3x score)", YELLOW)

        pyxel.text(SCREEN_W // 2 - 36, 150, "Click switches to", WHITE)
        pyxel.text(SCREEN_W // 2 - 36, 162, "divert marbles!", WHITE)

        pyxel.text(SCREEN_W // 2 - 40, 190, "60 second timer", WHITE)

        blink = (self.frame // 30) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 48, 218, "PRESS SPACE to start", YELLOW)

        # Demo marbles rolling
        self._draw_demo_marbles()

    def _draw_demo_marbles(self) -> None:
        t = self.frame * 1.5
        for i in range(4):
            x = 160.0
            y = 50.0 + (t + i * 40.0) % (SCREEN_H - 50)
            color = MARBLE_COLORS[i]
            pyxel.circ(int(x), int(y), 5, color)
            pyxel.circb(int(x), int(y), 5, BLACK)
            pyxel.pset(int(x) - 2, int(y) - 2, WHITE)

    def _draw_game_over_overlay(self) -> None:
        for y in range(SCREEN_H // 2 - 55, SCREEN_H // 2 + 55):
            for x in range(SCREEN_W // 2 - 85, SCREEN_W // 2 + 85, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, BLACK)

        pyxel.rectb(SCREEN_W // 2 - 85, SCREEN_H // 2 - 55, 170, 110, RED)
        pyxel.text(SCREEN_W // 2 - 24, SCREEN_H // 2 - 45, "GAME OVER", RED)

        score_str = f"Score: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_str) * 4, SCREEN_H // 2 - 25, score_str, WHITE)

        hi_str = f"Best: {self.high_score}"
        pyxel.text(SCREEN_W // 2 - len(hi_str) * 4, SCREEN_H // 2 - 13, hi_str, YELLOW)

        combo_str = f"Max Combo: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_str) * 4, SCREEN_H // 2 - 1, combo_str, GREEN)

        if self.heat >= HEAT_MAX:
            pyxel.text(SCREEN_W // 2 - 32, SCREEN_H // 2 + 15, "Overheated!", RED)
        else:
            pyxel.text(SCREEN_W // 2 - 24, SCREEN_H // 2 + 15, "Time Up!", WHITE)

        blink = (self.frame // 30) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 52, SCREEN_H // 2 + 35, "PRESS SPACE to retry", YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
