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

TANK_COLORS: list[int] = [RED, YELLOW, DARK_BLUE, WHITE]
TANK_LABELS: list[str] = ["RED", "YEL", "BLU", "WHT"]

SCREEN_W = 320
SCREEN_H = 240

ORDER_SPEED_BASE = 0.4
ORDER_SPAWN_INTERVAL_BASE = 120
MAX_ORDERS = 4
ORDER_Y_POSITIONS = [70, 100, 130, 160]
ORDER_X_SPAWN = 320.0
ORDER_X_DEAD = 20.0
ORDER_W = 40
ORDER_H = 16

TANK_Y = 220
TANK_W = 70
TANK_H = 18
TANK_GAP = 10
TANK_START_X = 5

PALETTE_RADIUS = 10
PALETTE_X = 160
PALETTE_Y = 200

COMBO_THRESHOLD = 4
SUPER_DURATION = 300
HEAT_MAX = 100.0
HEAT_MISMATCH = 20.0
HEAT_EXPIRE = 15.0
HEAT_DECAY = 0.05
TIME_LIMIT = 60

BASE_SCORE = 10

FPS = 30
HUD_H = 24
POPUP_LIFE = 30


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Order:
    x: float
    y: float
    color: int
    active: bool = True
    slot: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        if Game._initialized:
            return
        Game._initialized = True

        pyxel.init(SCREEN_W, SCREEN_H, title="Chroma Mix", display_scale=2, fps=FPS)
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
        self.timer: int = TIME_LIMIT * FPS
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.super_flash: int = 0
        self.palette_color: int = -1
        self.palette_flash: int = 0
        self.spawn_timer: int = ORDER_SPAWN_INTERVAL_BASE
        self.spawn_interval: int = ORDER_SPAWN_INTERVAL_BASE
        self.orders: list[Order] = []
        self.particles: list[Particle] = []
        self.score_popups: list[tuple[float, float, int, int, int]] = []
        self.shake_timer: int = 0
        self.frame: int = 0
        self._occupied_slots: set[int] = set()

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = TIME_LIMIT * FPS
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.super_flash = 0
        self.palette_color = -1
        self.palette_flash = 0
        self.spawn_timer = ORDER_SPAWN_INTERVAL_BASE
        self.spawn_interval = ORDER_SPAWN_INTERVAL_BASE
        self.orders.clear()
        self.particles.clear()
        self.score_popups.clear()
        self.shake_timer = 0
        self._occupied_slots.clear()

    # --- Update ---

    def _update(self) -> None:
        self.frame += 1

        if self.shake_timer > 0:
            self.shake_timer -= 1
            if self.shake_timer > 0:
                sx = self._rng.randint(-3, 3)
                sy = self._rng.randint(-3, 3)
                try:
                    pyxel.camera(sx, sy)
                except Exception:
                    pass
            else:
                try:
                    pyxel.camera(0, 0)
                except Exception:
                    pass

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            bx = SCREEN_W // 2 - 30
            by = 200
            if bx <= pyxel.mouse_x <= bx + 60 and by <= pyxel.mouse_y <= by + 16:
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

        if self.palette_flash > 0:
            self.palette_flash -= 1

        self._update_heat()
        self._update_super_mode()
        self._update_particles()
        self._update_score_popups()
        self._update_orders()
        self._update_spawning()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

    # --- Spawning ---

    def _update_spawning(self) -> None:
        elapsed = TIME_LIMIT * FPS - self.timer
        periods = elapsed // (10 * FPS)
        self.spawn_interval = max(40, ORDER_SPAWN_INTERVAL_BASE - periods * 10)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0 and len(self.orders) < MAX_ORDERS:
            self.spawn_timer = self.spawn_interval
            order = self._spawn_order()
            if order is not None:
                self.orders.append(order)

    def _spawn_order(self) -> Order | None:
        available = [s for s in range(4) if s not in self._occupied_slots]
        if not available:
            return None
        slot = self._rng.choice(available)
        color = self._rng.choice(TANK_COLORS)
        y = ORDER_Y_POSITIONS[slot]
        self._occupied_slots.add(slot)
        return Order(x=ORDER_X_SPAWN, y=float(y), color=color, active=True, slot=slot)

    # --- Orders ---

    def _update_orders(self) -> None:
        elapsed = TIME_LIMIT * FPS - self.timer
        periods = elapsed // (10 * FPS)
        speed = min(2.0, ORDER_SPEED_BASE + periods * 0.05)

        if self.super_mode:
            for o in self.orders:
                if o.active:
                    self._match_order(o)
                    o.active = False
                    self._occupied_slots.discard(o.slot)
            self.orders = [o for o in self.orders if o.active]
            return

        for o in self.orders:
            if not o.active:
                continue
            o.x -= speed
            if o.x <= ORDER_X_DEAD:
                o.active = False
                self._occupy_heat(HEAT_EXPIRE)
                self._occupied_slots.discard(o.slot)

        self.orders = [o for o in self.orders if o.active]

    def _get_nearest_order_idx(self) -> int:
        best_idx = -1
        best_x = -999.0
        for i, o in enumerate(self.orders):
            if o.active and o.x > best_x:
                best_x = o.x
                best_idx = i
        return best_idx

    # --- Click Handler ---

    def _handle_click(self, x: int, y: int) -> None:
        if self.palette_flash > 0:
            return

        for i in range(4):
            tx = TANK_START_X + i * (TANK_W + TANK_GAP)
            if tx <= x <= tx + TANK_W and TANK_Y <= y <= TANK_Y + TANK_H:
                self._select_color(TANK_COLORS[i])
                return

    def _select_color(self, color: int) -> None:
        self.palette_color = color
        self.palette_flash = 3

        nearest_idx = self._get_nearest_order_idx()
        if nearest_idx < 0:
            return

        nearest = self.orders[nearest_idx]
        if self.super_mode or nearest.color == color:
            self._try_match(nearest)
        else:
            self._mismatch(color)

    def _try_match(self, order: Order) -> None:
        self.combo += 1
        mult = self._compute_combo_multiplier(self.combo)
        gain = BASE_SCORE * mult
        if self.super_mode:
            gain *= 3
        self.score += gain

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= COMBO_THRESHOLD and not self.super_mode:
            self._activate_super()

        self._spawn_collect_particles(
            order.x + ORDER_W / 2, order.y + ORDER_H / 2, order.color, 8
        )
        self.score_popups.append(
            (order.x + ORDER_W / 2, order.y, gain, POPUP_LIFE, order.color)
        )

        if self.combo > 1 and not self.super_mode:
            combo_color = GREEN if self.combo >= 4 else WHITE
            self.score_popups.append(
                (order.x + ORDER_W / 2, order.y - 10, 0, POPUP_LIFE, combo_color)
            )

        order.active = False
        self._occupied_slots.discard(order.slot)

    def _match_order(self, order: Order) -> None:
        self.combo += 1
        mult = self._compute_combo_multiplier(self.combo)
        gain = BASE_SCORE * mult * 3
        self.score += gain

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        self._spawn_collect_particles(
            order.x + ORDER_W / 2, order.y + ORDER_H / 2, order.color, 8
        )
        self.score_popups.append(
            (order.x + ORDER_W / 2, order.y, gain, POPUP_LIFE, order.color)
        )

    def _mismatch(self, color: int) -> None:
        self._occupy_heat(HEAT_MISMATCH)
        self.combo = 0
        self.shake_timer = 5

        for _ in range(4):
            self.particles.append(
                Particle(
                    x=float(PALETTE_X),
                    y=float(PALETTE_Y),
                    vx=self._rng.uniform(-1.0, 1.0),
                    vy=self._rng.uniform(-2.0, -0.5),
                    life=self._rng.randint(10, 20),
                    color=GRAY,
                )
            )

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

    # --- Heat ---

    def _occupy_heat(self, amount: float) -> None:
        self.heat += amount
        if self.heat > HEAT_MAX:
            self.heat = HEAT_MAX

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
            self._spawn_super_particles()

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.super_flash = 0
        self.score_popups.append((PALETTE_X, PALETTE_Y - 20, 0, 45, YELLOW))

        for _ in range(20):
            self.particles.append(
                Particle(
                    x=float(PALETTE_X),
                    y=float(PALETTE_Y),
                    vx=self._rng.uniform(-3.0, 3.0),
                    vy=self._rng.uniform(-4.0, -1.0),
                    life=self._rng.randint(20, 40),
                    color=self._rng.choice(TANK_COLORS),
                )
            )

        self.shake_timer = 8

    def _spawn_super_particles(self) -> None:
        if self.frame % 6 != 0:
            return
        edge = self._rng.randint(0, 3)
        if edge == 0:
            px = float(self._rng.randint(0, SCREEN_W))
            py = 0.0
        elif edge == 1:
            px = float(self._rng.randint(0, SCREEN_W))
            py = float(SCREEN_H)
        elif edge == 2:
            px = 0.0
            py = float(self._rng.randint(0, SCREEN_H))
        else:
            px = float(SCREEN_W)
            py = float(self._rng.randint(0, SCREEN_H))

        self.particles.append(
            Particle(
                x=px,
                y=py,
                vx=self._rng.uniform(-0.5, 0.5),
                vy=self._rng.uniform(-0.5, 0.5),
                life=self._rng.randint(15, 30),
                color=self._rng.choice(TANK_COLORS),
            )
        )

    # --- Particles ---

    def _spawn_collect_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
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
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_hud()
        self._draw_order_lanes()
        self._draw_orders()
        self._draw_palette()
        self._draw_tanks()
        self._draw_particles()
        self._draw_score_popups()

        if self.super_mode:
            self._draw_super_mode()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 40, "CHROMA MIX", WHITE)
        pyxel.text(SCREEN_W // 2 - 28, 52, "----------", GRAY)

        pyxel.text(SCREEN_W // 2 - 80, 72, "Mix paints to match orders!", WHITE)
        pyxel.text(SCREEN_W // 2 - 80, 84, "Click tanks to select color", WHITE)
        pyxel.text(SCREEN_W // 2 - 80, 96, "Same color = COMBO +score", GREEN)
        pyxel.text(SCREEN_W // 2 - 80, 108, "Wrong color = HEAT +20!", RED)
        pyxel.text(SCREEN_W // 2 - 80, 120, "COMBO x4 = SUPER MIX", YELLOW)
        pyxel.text(SCREEN_W // 2 - 80, 132, "3x score / auto-clear all", YELLOW)
        pyxel.text(SCREEN_W // 2 - 80, 144, "Miss orders = HEAT +15", ORANGE)
        pyxel.text(SCREEN_W // 2 - 80, 156, "HEAT >= 100 = Game Over", RED)
        pyxel.text(SCREEN_W // 2 - 80, 168, "60 second time limit", WHITE)

        for i in range(4):
            tx = TANK_START_X + i * (TANK_W + TANK_GAP)
            tcol = TANK_COLORS[i]
            pyxel.rect(tx, 185, TANK_W, TANK_H, tcol)
            pyxel.rectb(tx, 185, TANK_W, TANK_H, WHITE)
            label = TANK_LABELS[i]
            pyxel.text(tx + TANK_W // 2 - len(label) * 4, 185 + TANK_H // 2 - 4, label, BLACK if i == 3 else WHITE)

        bx = SCREEN_W // 2 - 30
        by = 210
        pyxel.rect(bx, by, 60, 16, GREEN)
        pyxel.rectb(bx, by, 60, 16, WHITE)
        pyxel.text(bx + 12, by + 4, "START", BLACK)

        blink = (self.frame // 15) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 56, 232, "or Press SPACE to start", YELLOW)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, HUD_H, NAVY)
        pyxel.line(0, HUD_H, SCREEN_W, HUD_H, GRAY)

        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        timer_sec = max(0, self.timer // FPS)
        timer_str = f"TIME:{timer_sec}"
        pyxel.text(SCREEN_W // 2 - len(timer_str) * 4, 2, timer_str, WHITE)

        combo_str = f"COMBO:{self.combo}"
        combo_color = (
            YELLOW
            if self.combo >= COMBO_THRESHOLD
            else (GREEN if self.combo >= 3 else WHITE)
        )
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

        heat_str = f"HEAT:{int(self.heat)}"
        pyxel.text(108, 2, heat_str, fill_color)

    def _draw_order_lanes(self) -> None:
        for slot_y in ORDER_Y_POSITIONS:
            pyxel.line(0, slot_y + ORDER_H + 4, SCREEN_W, slot_y + ORDER_H + 4, DARK_BLUE)

    def _draw_orders(self) -> None:
        for o in self.orders:
            if not o.active:
                continue
            x = int(o.x)
            y = int(o.y)

            if self.super_mode:
                color = self._super_rainbow_color()
            else:
                color = o.color

            pyxel.rect(x, y, ORDER_W, ORDER_H, color)
            pyxel.rectb(x, y, ORDER_W, ORDER_H, WHITE)

            label = "RED" if o.color == RED else "YEL" if o.color == YELLOW else "BLU" if o.color == DARK_BLUE else "WHT"
            pyxel.text(
                x + ORDER_W // 2 - len(label) * 4,
                y + ORDER_H // 2 - 4,
                label,
                BLACK if o.color == WHITE else WHITE,
            )

            if o.x <= ORDER_X_DEAD + 40 and not self.super_mode:
                warn = (self.frame // 10) % 2 == 0
                if warn:
                    pyxel.rectb(x - 2, y - 2, ORDER_W + 4, ORDER_H + 4, RED)

    def _draw_palette(self) -> None:
        if self.palette_color >= 0:
            flash = self.palette_flash > 0
            c = WHITE if flash else self.palette_color

            if self.super_mode:
                c = self._super_rainbow_color()

            pyxel.circ(PALETTE_X, PALETTE_Y, PALETTE_RADIUS, c)
            pyxel.circb(PALETTE_X, PALETTE_Y, PALETTE_RADIUS, WHITE)
            pyxel.pset(PALETTE_X - 3, PALETTE_Y - 3, WHITE)
        else:
            pyxel.circb(PALETTE_X, PALETTE_Y, PALETTE_RADIUS, WHITE)

        pyxel.text(PALETTE_X - 12, PALETTE_Y + 12, "MIX", GRAY)

    def _draw_tanks(self) -> None:
        for i in range(4):
            tx = TANK_START_X + i * (TANK_W + TANK_GAP)
            tcol = TANK_COLORS[i]

            if self.palette_color == TANK_COLORS[i] and self.palette_flash > 0:
                draw_col = WHITE
            else:
                draw_col = tcol

            pyxel.rect(tx, TANK_Y, TANK_W, TANK_H, draw_col)
            pyxel.rectb(tx, TANK_Y, TANK_W, TANK_H, WHITE)

            label = TANK_LABELS[i]
            text_x = tx + TANK_W // 2 - len(label) * 4
            text_y = TANK_Y + TANK_H // 2 - 4
            pyxel.text(text_x, text_y, label, BLACK if i == 3 else WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.15:
                s = 2
                pyxel.rect(int(p.x), int(p.y), s, s, p.color)

    def _draw_score_popups(self) -> None:
        for x, y, val, life, color in self.score_popups:
            alpha = life / POPUP_LIFE
            if alpha < 0.1:
                continue
            if val > 0:
                text = f"+{val}"
                if self.super_mode:
                    text = f"+{val}S"
                pyxel.text(int(x) - len(text) * 4, int(y), text, color)
            else:
                if self.super_mode:
                    pyxel.text(int(x) - 28, int(y), "SUPER MIX!", YELLOW)
                else:
                    combo_text = f"COMBO x{self.combo}!"
                    pyxel.text(int(x) - len(combo_text) * 4, int(y), combo_text, color)

    def _draw_super_mode(self) -> None:
        color_idx = (self.super_flash // 8) % len(TANK_COLORS)
        border_color = TANK_COLORS[color_idx]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, border_color)

        super_sec = self.super_timer / float(FPS)
        super_str = f"SUPER MIX! {super_sec:.1f}s"
        pyxel.text(SCREEN_W // 2 - len(super_str) * 4, HUD_H + 4, super_str, YELLOW)

    def _super_rainbow_color(self) -> int:
        idx = (self.super_flash // 8) % len(TANK_COLORS)
        return TANK_COLORS[idx]

    def _draw_game_over_overlay(self) -> None:
        ox = SCREEN_W // 2 - 85
        oy = SCREEN_H // 2 - 55
        for y in range(oy, oy + 110):
            for x in range(ox, ox + 170, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, BLACK)

        pyxel.rectb(ox, oy, 170, 110, RED)
        pyxel.text(SCREEN_W // 2 - 24, oy + 10, "GAME OVER", RED)

        score_str = f"Score: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_str) * 4, oy + 30, score_str, WHITE)

        hi_str = f"Best: {self.high_score}"
        pyxel.text(SCREEN_W // 2 - len(hi_str) * 4, oy + 42, hi_str, YELLOW)

        combo_str = f"Max Combo: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_str) * 4, oy + 54, combo_str, GREEN)

        if self.heat >= HEAT_MAX:
            pyxel.text(SCREEN_W // 2 - 32, oy + 70, "Overheated!", RED)
        else:
            pyxel.text(SCREEN_W // 2 - 24, oy + 70, "Time Up!", WHITE)

        blink = (self.frame // 15) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 52, oy + 90, "PRESS SPACE to retry", YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
