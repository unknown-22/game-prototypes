from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 190
THROWER_X = 48
RING_RADIUS = 16
RING_COUNT = 5
MIN_RING_GAP = 30
FPS = 30
TIMER_MAX = 1800
STAMINA_MAX = 100.0
SCORING_DELAY = 30
SUPER_DURATION = 300
MISS_HEAT = 10.0
MISMATCH_HEAT = 15.0
HEAT_DECAY = 0.02
HEAT_CAP = 100.0
STAMINA_PER_THROW = 25.0
STAMINA_RECHARGE = 0.10
GRAVITY = 0.15
CHARGE_RATE = 100.0 / 60.0

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

SHOT_COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "LIME", "BLUE", "YELLOW"]


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    SCORING = auto()
    GAME_OVER = auto()


@dataclass
class Ring:
    x: float
    color: int
    radius: int = RING_RADIUS
    active: bool = True


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


class Game:
    COLORS: ClassVar[list[int]] = SHOT_COLORS

    def __new__(cls, headless: bool = False) -> Game:
        obj = object.__new__(cls)
        obj._set_defaults()
        obj._headless = headless
        return obj

    def _set_defaults(self) -> None:
        self._headless: bool = False
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.stamina: float = STAMINA_MAX
        self.timer: int = TIMER_MAX
        self.shot_color_idx: int = 0
        self.charge_power: float = 0.0
        self.charging: bool = False
        self.shot_x: float = THROWER_X
        self.shot_y: float = GROUND_Y
        self.shot_vx: float = 0.0
        self.shot_vy: float = 0.0
        self.shot_active: bool = False
        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.super_timer: int = 0
        self.ghost_trail: list[tuple[float, float]] = []
        self.best_score: int = 0
        self.phase_timer: int = 0
        self.scoring_timer: int = 0
        self.rng: random.Random = random.Random()
        self.throw_count: int = 0
        self.color_switch_cooldown: int = 0
        self.best_throw_score: int = 0
        self.best_trail: list[tuple[float, float]] = []

    def __init__(self, headless: bool = False) -> None:
        if not headless:
            pyxel.init(SCREEN_W, SCREEN_H, title="PUT CHAIN", fps=FPS)
            pyxel.mouse(True)
            self.reset()
            pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.stamina = STAMINA_MAX
        self.timer = TIMER_MAX
        self.shot_color_idx = 0
        self.charge_power = 0.0
        self.charging = False
        self.shot_x = THROWER_X
        self.shot_y = GROUND_Y
        self.shot_vx = 0.0
        self.shot_vy = 0.0
        self.shot_active = False
        self.particles.clear()
        self.floating_texts.clear()
        self.super_timer = 0
        self.ghost_trail.clear()
        self.phase_timer = 0
        self.scoring_timer = 0
        self.throw_count = 0
        self.color_switch_cooldown = 0
        self.best_throw_score = 0
        self.best_trail.clear()
        self._spawn_rings()

    def _spawn_rings(self) -> None:
        self.rings.clear()
        x_min = 80
        x_max = 280
        min_gap = MIN_RING_GAP

        attempts = 0
        while len(self.rings) < RING_COUNT and attempts < 200:
            attempts += 1
            x = self.rng.uniform(x_min, x_max)
            if any(abs(x - r.x) < min_gap for r in self.rings):
                continue
            color = self.rng.choice(SHOT_COLORS)
            self.rings.append(Ring(x=x, color=color))

        self.rings.sort(key=lambda r: r.x)

    def _get_shot_color(self) -> int:
        return SHOT_COLORS[self.shot_color_idx]

    def _launch_shot(self, mouse_y: float) -> None:
        power = min(self.charge_power, 100.0)
        if self.stamina < 25.0:
            power = min(power, 50.0)

        self.shot_vx = self.rng.uniform(3.0, 3.5) + (power * 0.06)
        self.shot_vy = -power * 0.08 * max(0.1, (mouse_y / max(1, SCREEN_H)))

        self.shot_x = float(THROWER_X)
        self.shot_y = float(GROUND_Y - 20)
        self.shot_active = True
        self.charging = False

        self.stamina = max(0.0, self.stamina - STAMINA_PER_THROW)
        self.throw_count += 1

        if self.throw_count % 5 == 0:
            self._shuffle_ring_colors()

        if self._is_super():
            self._spawn_particles(THROWER_X, GROUND_Y - 20, 12, -1)

    def _shuffle_ring_colors(self) -> None:
        for ring in self.rings:
            ring.color = self.rng.choice(SHOT_COLORS)

    def _update_shot(self) -> None:
        if not self.shot_active:
            return
        self.shot_vy += GRAVITY
        self.shot_x += self.shot_vx
        self.shot_y += self.shot_vy
        if self.shot_y >= GROUND_Y:
            self.shot_y = float(GROUND_Y)
            self.shot_active = False
            self.phase = Phase.SCORING
            self.phase_timer = 0
            self._check_scoring()

    def _check_scoring(self) -> None:
        shot_color = self._get_shot_color()
        multiplier = 3.0 if self._is_super() else 1.0
        hit_any = False
        hit_match = False
        throw_score = 0

        for ring in self.rings:
            if not ring.active:
                continue
            dist = abs(self.shot_x - ring.x)
            if dist <= ring.radius:
                ring.active = False
                hit_any = True
                if self._is_super() or shot_color == ring.color:
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    points = int(100 * self.combo * multiplier)
                    throw_score += points
                    self.score += points
                    self._spawn_particles(ring.x, GROUND_Y, 10, ring.color)
                    self._spawn_floating_text(
                        ring.x, GROUND_Y - 10,
                        f"+{points}",
                        LIME if not self._is_super() else YELLOW,
                    )
                    if self.combo >= 2:
                        self._spawn_floating_text(
                            ring.x, GROUND_Y - 22,
                            f"COMBO x{self.combo}",
                            YELLOW,
                        )
                    hit_match = True
                else:
                    self.combo = 0
                    self.heat = min(HEAT_CAP, self.heat + MISMATCH_HEAT)
                    self._spawn_particles(ring.x, GROUND_Y, 5, RED)
                    self._spawn_floating_text(ring.x, GROUND_Y - 10, "WRONG!", RED)

        if not hit_any:
            self.combo = 0
            self.heat = min(HEAT_CAP, self.heat + MISS_HEAT)
            self._spawn_particles(self.shot_x, GROUND_Y, 4, GRAY)
            self._spawn_floating_text(self.shot_x, GROUND_Y - 10, "MISS!", GRAY)

        if hit_match and throw_score > self.best_throw_score:
            self.best_throw_score = throw_score
            self.best_trail = self.ghost_trail.copy()

        self._update_combos()
        self.scoring_timer = SCORING_DELAY
        self.ghost_trail.clear()

    def _update_combos(self) -> None:
        if self.combo >= 4 and self.super_timer == 0:
            self.super_timer = SUPER_DURATION
            self._spawn_floating_text(
                THROWER_X + 40, GROUND_Y - 40,
                "SUPER PUT!",
                YELLOW,
            )
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_heat(self) -> None:
        if self.heat >= HEAT_CAP:
            self.phase = Phase.GAME_OVER
            self._spawn_floating_text(
                SCREEN_W // 2, SCREEN_H // 2,
                "GAME OVER",
                RED,
            )
            if self.score > self.best_score:
                self.best_score = self.score
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            if color == -1:
                pcolor = self.rng.choice(SHOT_COLORS)
            else:
                pcolor = color
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-2.0, -0.5)
            life = self.rng.randint(15, 25) if color != -1 else self.rng.randint(20, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=pcolor)
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        life = 30
        if "SUPER" in text:
            life = 40
        elif "WRONG" in text or "MISS" in text:
            life = 25
        elif "GAME OVER" in text:
            life = 60
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _record_ghost_trail(self) -> None:
        if self.shot_active:
            self.ghost_trail.append((self.shot_x, self.shot_y))

    def _get_input(self) -> dict:
        if self._headless:
            return {"space": False, "space_p": False, "mouse_y": 0.0, "up": False, "down": False}
        return {
            "space": pyxel.btn(pyxel.KEY_SPACE),
            "space_p": pyxel.btnp(pyxel.KEY_SPACE),
            "mouse_y": float(pyxel.mouse_y),
            "up": pyxel.btnp(pyxel.KEY_UP),
            "down": pyxel.btnp(pyxel.KEY_DOWN),
        }

    def _update(self) -> None:
        inp = self._get_input()

        if self.phase == Phase.TITLE:
            self._update_title(inp)
        elif self.phase == Phase.AIMING:
            self._update_aiming(inp)
        elif self.phase == Phase.FLYING:
            self._update_flying()
        elif self.phase == Phase.SCORING:
            self._update_scoring(inp)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(inp)

        self._update_particles()
        self._update_floating_texts()
        self._update_heat()

    def _update_title(self, inp: dict) -> None:
        if inp["space_p"]:
            self.reset()
            self.phase = Phase.AIMING

    def _update_aiming(self, inp: dict) -> None:
        if self.color_switch_cooldown > 0:
            self.color_switch_cooldown -= 1

        if inp["up"] and self.color_switch_cooldown == 0:
            self.shot_color_idx = (self.shot_color_idx - 1) % len(SHOT_COLORS)
            self.color_switch_cooldown = 8
        if inp["down"] and self.color_switch_cooldown == 0:
            self.shot_color_idx = (self.shot_color_idx + 1) % len(SHOT_COLORS)
            self.color_switch_cooldown = 8

        if inp["space"]:
            self.charging = True
            self.charge_power = min(100.0, self.charge_power + CHARGE_RATE)
            if self.charge_power >= 100.0:
                mouse_y = inp["mouse_y"]
                self._launch_shot(mouse_y)
                self.phase = Phase.FLYING
                self.charge_power = 0.0
        elif self.charging:
            mouse_y = inp["mouse_y"]
            self._launch_shot(mouse_y)
            self.phase = Phase.FLYING
            self.charge_power = 0.0

        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return

        self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_RECHARGE)

    def _update_flying(self) -> None:
        self._update_shot()
        self._record_ghost_trail()
        self.timer -= 1
        if self.timer <= 0 and self.phase != Phase.SCORING:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
        self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_RECHARGE)

    def _update_scoring(self, inp: dict) -> None:
        self.scoring_timer -= 1
        self.timer -= 1
        self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_RECHARGE)
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return
        if self.scoring_timer <= 0:
            self.phase = Phase.AIMING
            for ring in self.rings:
                ring.active = True

    def _update_game_over(self, inp: dict) -> None:
        if inp["space_p"]:
            self.reset()
            self.phase = Phase.TITLE

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLYING, Phase.SCORING):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()

    def _draw_title(self) -> None:
        px = THROWER_X
        py = GROUND_Y - 20
        pyxel.tri(px - 4, py - 12, px + 4, py - 12, px, py - 18, PEACH)

        for x, y in ((px - 2, py - 4), (px + 2, py - 4), (px, py - 8)):
            pyxel.circ(x, y, 1, PEACH)

        pyxel.text(SCREEN_W // 2 - 28, 60, "PUT CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 44, 80, "Color-match shot put!", LIME)
        pyxel.text(SCREEN_W // 2 - 55, 100, "Hold SPACE: charge power", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 112, "Mouse Y: aim angle", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 124, "UP/DOWN: change shot color", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 136, "Same color hit = COMBO chain", LIME)
        pyxel.text(SCREEN_W // 2 - 55, 148, "Wrong color = COMBO reset + HEAT", RED)
        pyxel.text(SCREEN_W // 2 - 55, 160, "COMBO x4 = SUPER PUT!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 55, 172, "HEAT 100 = GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 55, 190, "60s to score as high as you can!", WHITE)
        pyxel.text(SCREEN_W // 2 - 45, 210, "SPACE to start", CYAN)
        if self.best_score > 0:
            pyxel.text(
                SCREEN_W // 2 - 30, 225, f"BEST: {self.best_score}", YELLOW
            )

    def _draw_game(self) -> None:
        self._draw_sky()
        self._draw_ground()
        self._draw_rings()
        self._draw_ghost_trail()
        self._draw_best_trail()
        if self.shot_active:
            self._draw_shot()
        self._draw_thrower()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_power_bar()

    def _draw_sky(self) -> None:
        for i in range(GROUND_Y):
            t = i / GROUND_Y
            if t < 0.5:
                col = NAVY
            elif t < 0.75:
                col = DARK_BLUE
            else:
                col = LIGHT_BLUE
            pyxel.line(0, i, SCREEN_W, i, col)

    def _draw_ground(self) -> None:
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, WHITE)
        pyxel.line(THROWER_X + 20, GROUND_Y, THROWER_X + 20, SCREEN_H, WHITE)

    def _draw_thrower(self) -> None:
        px = THROWER_X
        py = GROUND_Y - 20
        pyxel.tri(px - 4, py - 12, px + 4, py - 12, px, py - 18, PEACH)
        for x, y in ((px - 2, py - 4), (px + 2, py - 4), (px, py - 8)):
            pyxel.circ(x, y, 1, PEACH)
        pyxel.line(px, py - 8, px, py + 4, PEACH)
        pyxel.line(px, py - 2, px - 4, py - 8, PEACH)
        pyxel.line(px, py - 2, px + 4, py - 8, PEACH)
        pyxel.line(px, py + 4, px - 4, py + 12, PEACH)
        pyxel.line(px, py + 4, px + 4, py + 12, PEACH)

        if self.phase == Phase.AIMING:
            arm_angle = self.charge_power / 100.0 * (-1.2)
            color = self._get_shot_color()
            arm_len = 8
            ax = px + 2
            ay = py - 6
            import math
            ex = ax + math.cos(arm_angle) * arm_len
            ey = ay + math.sin(arm_angle) * arm_len
            pyxel.line(ax, ay, ex, ey, PEACH)
            pyxel.circ(ex, ey, 3, color)

        if self._is_super():
            ring_colors = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE, PINK]
            idx = (pyxel.frame_count // 3) % len(ring_colors)
            pyxel.circb(px, py - 10, 10, ring_colors[idx])

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if not ring.active:
                continue
            pyxel.circb(ring.x, GROUND_Y, ring.radius, ring.color)
            pyxel.circb(ring.x, GROUND_Y, ring.radius - 2, ring.color)
            pyxel.circb(ring.x, GROUND_Y, ring.radius - 4, ring.color)

    def _draw_shot(self) -> None:
        color = self._get_shot_color()
        if self._is_super():
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            color = rainbow[(pyxel.frame_count // 4) % len(rainbow)]
        pyxel.circ(int(self.shot_x), int(self.shot_y), 6, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 2, p.color)
            if p.life > 10:
                pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 14, f"COMBO: {self.combo}", YELLOW if self.combo >= 3 else WHITE)
        pyxel.text(4, 24, f"MAX: {self.max_combo}", LIME)
        pyxel.text(4, 34, f"BEST: {self.best_score}", YELLOW)

        secs = max(0, self.timer // FPS)
        timer_color = WHITE
        if secs <= 10:
            timer_color = RED
        elif secs <= 20:
            timer_color = ORANGE
        pyxel.text(SCREEN_W // 2 - 16, 4, f"TIME: {secs}s", timer_color)

        shot_color = self._get_shot_color()
        color_name = COLOR_NAMES[self.shot_color_idx]
        pyxel.text(SCREEN_W - 70, 4, "COLOR:", WHITE)
        pyxel.circ(SCREEN_W - 14, 9, 4, shot_color)
        pyxel.text(SCREEN_W - 70, 14, color_name, shot_color)

        pyxel.text(4, GROUND_Y + 4, "HEAT", WHITE)
        heat_w = 80
        heat_h = 6
        pyxel.rectb(4, GROUND_Y + 12, heat_w, heat_h, WHITE)
        heat_fill = int(heat_w * self.heat / HEAT_CAP)
        heat_color = LIME
        if self.heat > 60:
            heat_color = ORANGE
        if self.heat > 80:
            heat_color = RED
        pyxel.rect(4, GROUND_Y + 12, heat_fill, heat_h, heat_color)

        pyxel.text(4, GROUND_Y + 20, "STAMINA", WHITE)
        stam_w = 80
        stam_h = 6
        pyxel.rectb(4, GROUND_Y + 28, stam_w, stam_h, WHITE)
        stam_fill = int(stam_w * self.stamina / STAMINA_MAX)
        stam_color = LIME if self.stamina >= 50 else ORANGE if self.stamina >= 25 else RED
        pyxel.rect(4, GROUND_Y + 28, stam_fill, stam_h, stam_color)

        if self._is_super():
            super_secs = self.super_timer // FPS
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            color = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            pyxel.text(SCREEN_W // 2 - 30, 20, f"SUPER! {super_secs}s", color)

    def _draw_power_bar(self) -> None:
        if self.phase != Phase.AIMING and self.charge_power <= 0:
            return
        bar_w = 100
        bar_h = 8
        bx = THROWER_X - 10
        by = GROUND_Y + 40
        pyxel.rectb(bx, by, bar_w, bar_h, WHITE)
        fill_w = int(bar_w * self.charge_power / 100.0)
        bar_color = LIME
        if self.charge_power > 50:
            bar_color = YELLOW
        if self.charge_power > 80:
            bar_color = RED
        if self.charge_power > 95:
            bar_color = ORANGE
        pyxel.rect(bx, by, fill_w, bar_h, bar_color)

    def _draw_ghost_trail(self) -> None:
        for tx, ty in self.ghost_trail:
            pyxel.circ(int(tx), int(ty), 1, CYAN)

    def _draw_best_trail(self) -> None:
        for tx, ty in self.best_trail:
            pyxel.circ(int(tx), int(ty), 1, ORANGE)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 35, 140, 60, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 35, 140, 60, RED)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 25, "GAME OVER", RED)
        pyxel.text(
            SCREEN_W // 2 - 35, SCREEN_H // 2 - 10,
            f"SCORE: {self.score}",
            WHITE,
        )
        if self.score >= self.best_score and self.score > 0:
            pyxel.text(
                SCREEN_W // 2 - 25, SCREEN_H // 2,
                "NEW BEST!",
                YELLOW,
            )
        pyxel.text(
            SCREEN_W // 2 - 45, SCREEN_H // 2 + 12,
            "SPACE to retry",
            CYAN,
        )


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
