"""SWIM CHAIN — Color-match swimming through a pool.

Core fun moment: 同じ色のブイを連続でタッチしてコンボを繋ぎ、
SUPER SWIMで一気に加速し敵を突破するのが面白い
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60
FONT_PATH = Path(__file__).with_name("k8x12.bdf")

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

PLAYER_RADIUS = 8
LANE_COUNT = 4
LANE_H = 48
LANE_Y_START = 24
BUOY_SPACING = 80
BUOY_RADIUS = 8
BUBBLE_RADIUS = 5
PREDATOR_RADIUS = 12
COMBO_THRESHOLD = 4
SUPER_DURATION = 300
OXYGEN_MAX = 100.0
OXYGEN_DECAY = 0.03
OXYGEN_BUBBLE_REPLENISH = 25.0
HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_WRONG_COLOR = 15.0
AUTO_SCROLL_SPEED = 0.5
SUPER_SPEED_MULT = 2.0
PLAYER_SPEED = 3.0
SPAWN_INTERVAL = 120
MAX_PREDATORS = 8
BUOY_COLORS: tuple[int, int, int, int] = (RED, GREEN, YELLOW, CYAN)

PLAYER_START_X = 60.0


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SUPER = auto()
    GAME_OVER = auto()


@dataclass
class Buoy:
    x: float
    y: float
    color: int
    active: bool = True
    radius: int = BUOY_RADIUS


@dataclass
class Bubble:
    x: float
    y: float
    radius: int = BUBBLE_RADIUS
    active: bool = True


@dataclass
class Predator:
    x: float
    y: float
    vy: float = 0.0
    active: bool = True
    radius: int = PREDATOR_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    life: int = 20
    color: int = 7
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int = 30
    color: int = 7
    vy: float = -1.0


def _lane_y(lane: int) -> float:
    return float(LANE_Y_START + lane * LANE_H + LANE_H // 2)


LANE_YS: tuple[float, float, float, float] = (
    _lane_y(0), _lane_y(1), _lane_y(2), _lane_y(3)
)


class Game:
    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SWIM CHAIN", fps=FPS, display_scale=DISPLAY_SCALE)
        _ = pyxel.Font(str(FONT_PATH))
        self._rng = random.Random()
        self._frame_count: int = 0
        self.buoys: list[Buoy] = []
        self.bubbles: list[Bubble] = []
        self.predators: list[Predator] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x: float = PLAYER_START_X
        self.player_y: float = SCREEN_H / 2
        self.player_vy: float = 0.0
        self.oxygen: float = OXYGEN_MAX
        self.oxygen_decay: float = OXYGEN_DECAY
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.distance: float = 0.0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.scroll_x: float = 0.0
        self._spawn_timer: int = 0
        self.buoys.clear()
        self.bubbles.clear()
        self.predators.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._shake_frames = 0

    @property
    def super_mode(self) -> bool:
        return self.super_timer > 0

    # ── Spawn Logic ────────────────────────────────────────────────────

    def _spawn_buoys(self) -> None:
        right_edge = self.scroll_x + SCREEN_W + BUOY_SPACING
        for lane in range(LANE_COUNT):
            has_buoy_near = any(
                b.x > self.scroll_x + SCREEN_W and b.y == LANE_YS[lane]
                for b in self.buoys
            )
            if has_buoy_near:
                continue
            bx = right_edge + self._rng.uniform(0, BUOY_SPACING)
            by = LANE_YS[lane]
            color = self._rng.choice(BUOY_COLORS)
            self.buoys.append(Buoy(x=bx, y=by, color=color))

    def _spawn_bubbles(self) -> None:
        if self._rng.random() < 0.02:
            bx = self.scroll_x + SCREEN_W + self._rng.uniform(0, 100)
            by = self._rng.uniform(20, SCREEN_H - 20)
            self.bubbles.append(Bubble(x=bx, y=by))

    def _spawn_predator(self) -> None:
        if len([p for p in self.predators if p.active]) >= MAX_PREDATORS:
            return
        px = self.scroll_x + SCREEN_W + self._rng.uniform(0, 60)
        py = self._rng.uniform(20, SCREEN_H - 20)
        self.predators.append(Predator(x=px, y=py, vy=self._rng.uniform(-0.3, 0.3)))

    # ── Update Methods ─────────────────────────────────────────────────

    def _update_buoys(self) -> None:
        for b in self.buoys[:]:
            if b.x < self.scroll_x - BUOY_RADIUS * 2:
                self.buoys.remove(b)

    def _update_bubbles(self) -> None:
        for b in self.bubbles[:]:
            if b.x < self.scroll_x - BUBBLE_RADIUS * 2:
                self.bubbles.remove(b)

    def _update_predators(self) -> None:
        for p in self.predators[:]:
            p.x -= AUTO_SCROLL_SPEED * 0.8
            p.y += p.vy
            if p.y < 10 or p.y > SCREEN_H - 10:
                p.vy *= -1
            if p.x < self.scroll_x - PREDATOR_RADIUS * 2:
                self.predators.remove(p)

    def _check_buoy_collisions(self) -> None:
        for b in self.buoys:
            if not b.active:
                continue
            dx = self.player_x - b.x
            dy = self.player_y - b.y
            dist = math.hypot(dx, dy)
            if dist < PLAYER_RADIUS + b.radius:
                b.active = False
                if self.super_mode:
                    self._on_same_color_buoy(b.color)
                else:
                    self._on_buoy_hit(b)

    def _on_buoy_hit(self, b: Buoy) -> None:
        current_combo_color = BUOY_COLORS[self.combo % 4] if self.combo > 0 else None
        if self.combo > 0 and b.color == current_combo_color:
            self._on_same_color_buoy(b.color)
        elif self.combo == 0:
            self.combo = 1
            self.max_combo = max(self.max_combo, self.combo)
            pts = 10
            self.score += pts
            self._spawn_floating_text(self.player_x, self.player_y - 10, f"+{pts}", b.color)
            self._spawn_particles(self.player_x, self.player_y, 5, b.color)
        else:
            self._on_wrong_color_buoy()

    def _on_same_color_buoy(self, color: int) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        pts = 10 * (1 + self.combo // 2)
        self.score += pts
        self._spawn_floating_text(self.player_x, self.player_y - 10, f"+{pts}", color)
        self._spawn_particles(self.player_x, self.player_y, 5, color)
        if self.combo >= COMBO_THRESHOLD and not self.super_mode:
            self._activate_super()

    def _on_wrong_color_buoy(self) -> None:
        self.combo = 0
        self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG_COLOR)
        self._spawn_particles(self.player_x, self.player_y, 3, RED)
        self._spawn_floating_text(self.player_x, self.player_y - 10, "MISS", RED)

    def _check_predator_collisions(self) -> None:
        for p in self.predators:
            if not p.active:
                continue
            dx = self.player_x - p.x
            dy = self.player_y - p.y
            dist = math.hypot(dx, dy)
            if dist < PLAYER_RADIUS + p.radius:
                if self.super_mode:
                    p.active = False
                    self._spawn_particles(p.x, p.y, 12, LIME)
                    self.score += 50
                else:
                    p.active = False
                    self.oxygen -= 30.0 + self.heat / 5.0
                    self.heat = min(HEAT_MAX, self.heat + 10.0)
                    self.combo = 0
                    self._spawn_particles(self.player_x, self.player_y, 10, RED)
                    self._spawn_floating_text(self.player_x, self.player_y - 10, "-O2!", RED)
                    self._shake_frames = 6

    def _check_bubble_collisions(self) -> None:
        for b in self.bubbles:
            if not b.active:
                continue
            dx = self.player_x - b.x
            dy = self.player_y - b.y
            dist = math.hypot(dx, dy)
            if dist < PLAYER_RADIUS + b.radius:
                b.active = False
                self.oxygen = min(OXYGEN_MAX, self.oxygen + OXYGEN_BUBBLE_REPLENISH)
                self._spawn_particles(b.x, b.y, 3, LIGHT_BLUE)
                self._spawn_floating_text(b.x, b.y - 5, "+O2", LIGHT_BLUE)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(self.player_x, self.player_y - 25, "SUPER SWIM!", LIME)
        self._spawn_particles(self.player_x, self.player_y, 20, LIME)
        self._spawn_particles(self.player_x, self.player_y, 20, YELLOW)
        self._spawn_particles(self.player_x, self.player_y, 20, CYAN)
        self._spawn_particles(self.player_x, self.player_y, 20, RED)
        self._shake_frames = 8

    def _update_super(self) -> None:
        if self.super_timer <= 0:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_timer = 0
            self.combo = 0

    def _update_oxygen(self) -> None:
        self.oxygen -= self.oxygen_decay
        if self.oxygen <= 0:
            self.oxygen = 0
            if self.phase == Phase.PLAYING:
                self.phase = Phase.GAME_OVER
                self._spawn_particles(self.player_x, self.player_y, 30, RED)
                self._shake_frames = 4

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX and self.phase == Phase.PLAYING and not self.super_mode:
            self.phase = Phase.GAME_OVER
            self._spawn_particles(self.player_x, self.player_y, 40, RED)
            self._spawn_particles(self.player_x, self.player_y, 20, YELLOW)
            self._shake_frames = 4
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy -= 0.05
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 1.0)
            life = self._rng.randint(10, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    # ── Update ─────────────────────────────────────────────────────────

    def update(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1

        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.SUPER:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING
            self._spawn_buoys()

    def _update_playing(self) -> None:
        self._frame_count += 1
        speed = AUTO_SCROLL_SPEED * (SUPER_SPEED_MULT if self.super_mode else 1.0)
        self.scroll_x += speed
        self.distance += speed

        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.player_y -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.player_y += PLAYER_SPEED
        self.player_y = max(PLAYER_RADIUS, min(SCREEN_H - PLAYER_RADIUS, self.player_y))

        self._update_oxygen()
        self._update_super()
        self._update_heat()
        self._spawn_buoys()
        self._spawn_bubbles()
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_predator()
            self._spawn_timer = SPAWN_INTERVAL
        self._update_buoys()
        self._update_bubbles()
        self._update_predators()
        self._check_buoy_collisions()
        self._check_predator_collisions()
        self._check_bubble_collisions()
        self._update_particles()
        self._update_floating_texts()
        self.score += int(self.distance * 0.01)

        if self.phase != Phase.GAME_OVER:
            pass

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.TITLE

    # ── Draw ───────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self._shake_frames > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING | Phase.SUPER:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game()
                self._draw_game_over()

    def _draw_water(self) -> None:
        water_colors = (DARK_BLUE, NAVY, DARK_BLUE, NAVY, DARK_BLUE, NAVY, DARK_BLUE)
        for i, c in enumerate(water_colors):
            pyxel.rect(0, i * 12, SCREEN_W, 12, c)

    def _draw_lanes(self) -> None:
        for lane in range(LANE_COUNT):
            ly = int(LANE_YS[lane])
            for x in range(0, SCREEN_W, 16):
                offset = int(self.scroll_x * 0.5) % 16
                px = x - offset
                if px < -8:
                    px += SCREEN_W + 16
                pyxel.line(px, ly, px + 6, ly, LIGHT_BLUE)

    def _draw_super_border(self) -> None:
        if not self.super_mode:
            return
        rainbow = (RED, YELLOW, LIME, CYAN, DARK_BLUE)
        for i in range(4):
            color = rainbow[(pyxel.frame_count // 4 + i) % len(rainbow)]
            pyxel.rectb(2 + i, 2 + i, SCREEN_W - 4 - i * 2, SCREEN_H - 4 - i * 2, color)

    def _draw_swimmer(self) -> None:
        sx = int(self.player_x)
        sy = int(self.player_y)
        body_color = PEACH
        if self.super_mode:
            rainbow = (RED, YELLOW, LIME, CYAN, DARK_BLUE)
            body_color = rainbow[(pyxel.frame_count // 4) % len(rainbow)]

        pyxel.circ(sx, sy, PLAYER_RADIUS, body_color)
        pyxel.circb(sx, sy, PLAYER_RADIUS, WHITE)
        pyxel.rect(sx - 3, sy - 2, 2, 4, WHITE)
        pyxel.rect(sx - 1, sy - 3, 2, 6, BLACK)
        pyxel.tri(
            sx - PLAYER_RADIUS, sy - 4,
            sx - PLAYER_RADIUS, sy + 4,
            sx - PLAYER_RADIUS - 8, sy,
            WHITE,
        )

    def _draw_buoys(self) -> None:
        for b in self.buoys:
            if not b.active:
                continue
            bx = int(b.x - self.scroll_x)
            if bx < -BUOY_RADIUS or bx > SCREEN_W + BUOY_RADIUS:
                continue
            by = int(b.y)
            pyxel.circ(bx, by, b.radius, b.color)
            pyxel.circb(bx, by, b.radius, WHITE)

    def _draw_bubbles(self) -> None:
        for b in self.bubbles:
            if not b.active:
                continue
            bx = int(b.x - self.scroll_x)
            if bx < -BUBBLE_RADIUS or bx > SCREEN_W + BUBBLE_RADIUS:
                continue
            by = int(b.y)
            pyxel.circb(bx, by, b.radius, LIGHT_BLUE)
            pyxel.circb(bx + 1, by - 1, b.radius - 2, WHITE)

    def _draw_predators(self) -> None:
        for p in self.predators:
            if not p.active:
                continue
            px = int(p.x - self.scroll_x)
            if px < -PREDATOR_RADIUS * 2 or px > SCREEN_W + PREDATOR_RADIUS * 2:
                continue
            py_ = int(p.y)
            pyxel.tri(
                px + PREDATOR_RADIUS, py_ - 8,
                px + PREDATOR_RADIUS, py_ + 8,
                px - PREDATOR_RADIUS, py_,
                GRAY,
            )
            pyxel.tri(
                px + PREDATOR_RADIUS - 2, py_ - 4,
                px + PREDATOR_RADIUS - 2, py_ + 4,
                px - PREDATOR_RADIUS + 2, py_,
                BLACK,
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.2:
                px = int(p.x - self.scroll_x) if not self.super_mode else int(p.x - self.scroll_x)
                pyxel.pset(px, int(p.y), p.color)
            else:
                px = int(p.x)
                pyxel.pset(px, int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 0.3:
                px = int(ft.x - self.scroll_x)
                pyxel.text(px - len(ft.text) * 4 // 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        oxy_bar_x = 4
        oxy_bar_w = 80
        oxy_bar_y = 4
        oxy_bar_h = 8
        oxy_pct = self.oxygen / OXYGEN_MAX
        oxy_color = RED if oxy_pct < 0.3 else YELLOW if oxy_pct < 0.6 else CYAN
        pyxel.rectb(oxy_bar_x, oxy_bar_y, oxy_bar_w, oxy_bar_h, WHITE)
        pyxel.rect(oxy_bar_x, oxy_bar_y, int(oxy_bar_w * oxy_pct), oxy_bar_h, oxy_color)
        pyxel.text(oxy_bar_x + 2, oxy_bar_y + 10, "O2", oxy_color)

        heat_bar_x = SCREEN_W - 84
        heat_bar_w = 80
        heat_bar_y = 4
        heat_bar_h = 8
        heat_pct = self.heat / HEAT_MAX
        heat_color = RED if heat_pct > 0.7 else YELLOW if heat_pct > 0.4 else GREEN
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, WHITE)
        pyxel.rect(heat_bar_x, heat_bar_y, int(heat_bar_w * heat_pct), heat_bar_h, heat_color)
        pyxel.text(heat_bar_x - 18, heat_bar_y + 10, "HEAT", heat_color)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 4 // 2, 4, score_text, WHITE)

        combo_text = f"COMBO: x{self.combo}"
        combo_color = LIME if self.combo >= COMBO_THRESHOLD else YELLOW if self.combo >= 2 else WHITE
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 4 // 2, 16, combo_text, combo_color)

        if self.super_mode:
            super_left = max(0, self.super_timer * heat_bar_w // SUPER_DURATION)
            pyxel.rect(heat_bar_x, heat_bar_y + 16, super_left, 4, LIME)
            label = "SUPER"
            pyxel.text(heat_bar_x + heat_bar_w // 2 - len(label) * 4 // 2, heat_bar_y + 14, label, LIME)

    def _draw_title(self) -> None:
        self._draw_water()
        self._draw_lanes()

        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, CYAN)
        self._text_center(SCREEN_W // 2, 30, "SWIM CHAIN", WHITE)
        self._text_center(SCREEN_W // 2, 46, "COLOR-MATCH SWIMMING", GRAY)

        self._text_center(SCREEN_W // 2, 80, "HOW TO PLAY", WHITE)
        y = 96
        for i, c in enumerate(BUOY_COLORS):
            text = "TOUCH SAME-COLOR BUOYS IN A ROW"
            if i == 0:
                self._text_center(SCREEN_W // 2, y, text, c)
                y += 14
        self._text_center(SCREEN_W // 2, y + 4, "TO BUILD COMBO CHAIN", YELLOW)
        self._text_center(SCREEN_W // 2, y + 22, "COMBOx4 = SUPER SWIM!", LIME)
        self._text_center(SCREEN_W // 2, y + 40, "DODGE PREDATORS", RED)
        self._text_center(SCREEN_W // 2, y + 54, "COLLECT BUBBLES FOR O2", LIGHT_BLUE)

        self._text_center(SCREEN_W // 2, y + 80, "UP/DOWN or W/S: MOVE", WHITE)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(SCREEN_W // 2, y + 98, "PRESS SPACE TO START", WHITE)

        buoys_y = 190
        for i, c in enumerate(BUOY_COLORS):
            bx = 100 + i * 40
            pyxel.circ(bx, buoys_y, BUOY_RADIUS, c)
            pyxel.circb(bx, buoys_y, BUOY_RADIUS, WHITE)

    def _draw_game(self) -> None:
        self._draw_water()
        self._draw_lanes()
        self._draw_super_border()
        self._draw_buoys()
        self._draw_bubbles()
        self._draw_predators()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_swimmer()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        overlay_y = SCREEN_H // 2 - 60
        pyxel.rect(0, overlay_y, SCREEN_W, 120, BLACK)
        pyxel.rectb(0, overlay_y, SCREEN_W, 120, WHITE)
        self._text_center(SCREEN_W // 2, SCREEN_H // 2 - 48, "GAME OVER", RED)
        self._text_center(SCREEN_W // 2, SCREEN_H // 2 - 28, f"SCORE: {self.score}", WHITE)
        self._text_center(SCREEN_W // 2, SCREEN_H // 2 - 10, f"MAX COMBO: x{self.max_combo}", YELLOW)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(SCREEN_W // 2, SCREEN_H // 2 + 20, "PRESS SPACE TO RETRY", WHITE)

    @staticmethod
    def _text_center(x: int, y: int, text: str, color: int) -> None:
        px = x - len(text) * 4 // 2
        pyxel.text(px, y, text, color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
