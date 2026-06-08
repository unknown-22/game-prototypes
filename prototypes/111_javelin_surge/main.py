"""JAVELIN SURGE — Color-match javelin throw prototype."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

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

ZONE_COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
ZONE_COLOR_NAMES: dict[int, str] = {
    RED: "RED",
    GREEN: "GRN",
    DARK_BLUE: "BLU",
    YELLOW: "YEL",
}


# ── Data classes ──────────────────────────────────────────────────────────


@dataclass
class Zone:
    x: float
    color: int
    width: int = 24
    hit: bool = False
    passed: bool = False


@dataclass
class Javelin:
    x: float
    y: float
    vx: float
    vy: float
    angle: float
    power: float
    color: int
    landed: bool = False
    dist: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Phase enum ────────────────────────────────────────────────────────────


class Phase(StrEnum):
    TITLE = "TITLE"
    RUN_UP = "RUN_UP"
    THROW = "THROW"
    FLIGHT = "FLIGHT"
    RESULT = "RESULT"
    GAME_OVER = "GAME_OVER"


# ── Game logic class (testable, no pyxel input calls) ───────────────────


@dataclass
class Game:
    SCREEN_W: int = 320
    SCREEN_H: int = 240
    GROUND_Y: int = 160
    THROW_LINE_X: int = 260
    ATHLETE_X: int = 80
    RUN_SPEED: float = 3.0
    ZONE_SPACING: int = 64
    MAX_ATTEMPTS: int = 5
    MAX_HEAT: int = 5
    COMBO_FOR_SUPER: int = 4
    SUPER_DIST_MULT: float = 2.0
    SUPER_SCORE_MULT: int = 3
    GRAVITY: float = 0.15

    phase: Phase = Phase.TITLE
    attempt: int = 0
    world_x: float = 0.0
    combo: int = 0
    max_combo: int = 0
    heat: int = 0
    zones: list[Zone] = field(default_factory=list)
    javelin: Javelin | None = None
    particles: list[Particle] = field(default_factory=list)
    best_dist: float = 0.0
    total_score: int = 0
    super_throw: bool = False
    current_dist: float = 0.0
    current_score: int = 0
    mouse_drag_start: tuple[float, float] | None = None
    throw_power: float = 0.0
    throw_angle: float = 0.0
    zone_timer: float = 0.0
    result_timer: int = 0
    runway_length: float = 400.0
    zone_target_count: int = 8
    zones_spawned: int = 0
    _rng: random.Random = field(default_factory=random.Random)
    _last_matched_color: int | None = None

    def _spawn_zone(self) -> Zone:
        x = self.world_x + self.SCREEN_W + 8.0
        color = self._rng.choice(ZONE_COLORS)
        self.zones_spawned += 1
        return Zone(x=x, color=color, width=24)

    def _update_zones(self) -> None:
        self.world_x += self.RUN_SPEED
        for z in self.zones:
            z.x -= self.RUN_SPEED
            if z.x + z.width < self.ATHLETE_X - 16 and not z.passed:
                z.passed = True
                if not z.hit:
                    self._on_miss()

        self.zones = [z for z in self.zones if z.x > self.ATHLETE_X - 120]

        if self.zones_spawned < self.zone_target_count:
            if not self.zones or self.zones[-1].x < self.world_x + self.SCREEN_W - self.ZONE_SPACING:
                self.zones.append(self._spawn_zone())

        if self.zones_spawned >= self.zone_target_count and not self.zones:
            self._enter_throw_phase()

    def _try_match_zone(self) -> int | None:
        """Returns matched zone color if a hit, None if miss."""
        candidate: Zone | None = None
        for z in self.zones:
            if z.hit or z.passed:
                continue
            if z.x <= self.ATHLETE_X + 4 and z.x + z.width >= self.ATHLETE_X - 4:
                if candidate is None or z.x < candidate.x:
                    candidate = z
        if candidate is not None:
            candidate.hit = True
            return candidate.color
        return None

    def _on_match(self, color: int) -> None:
        if self._last_matched_color is not None and self._last_matched_color == color:
            self.combo += 1
        else:
            self.combo = 1
            if self._last_matched_color is not None:
                self.heat = min(self.heat + 1, self.MAX_HEAT)

        self._last_matched_color = color

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= self.COMBO_FOR_SUPER:
            self.super_throw = True

    def _on_miss(self) -> None:
        self.combo = 0
        self.heat = min(self.heat + 1, self.MAX_HEAT)

    def _enter_throw_phase(self) -> None:
        self.phase = Phase.THROW
        self.mouse_drag_start = None
        self.throw_power = 0.0
        self.throw_angle = 0.0

    def _throw_javelin(self, angle: float, power: float) -> None:
        vx = math.cos(angle) * power * 2.5
        vy = -math.sin(angle) * power * 2.5
        color = YELLOW if self.super_throw else DARK_BLUE
        self.javelin = Javelin(
            x=float(self.THROW_LINE_X),
            y=float(self.GROUND_Y) - 14.0,
            vx=vx,
            vy=vy,
            angle=angle,
            power=power,
            color=color,
        )
        self.phase = Phase.FLIGHT

    def _compute_flight(self, javelin: Javelin) -> float:
        """Returns landing distance (in world units, converted to meters)."""
        jx = float(javelin.x)
        jy = float(javelin.y)
        jvx = float(javelin.vx)
        jvy = float(javelin.vy)
        while jy < self.GROUND_Y:
            jx += jvx
            jy += jvy
            jvy += self.GRAVITY
        landing_x = jx - self.THROW_LINE_X
        dist = max(0.0, landing_x)
        dist_m = dist * 0.01
        if self.super_throw:
            dist_m *= self.SUPER_DIST_MULT
        return dist_m

    def _update_flight(self) -> None:
        if self.javelin is None:
            return
        j = self.javelin
        if j.landed:
            return
        j.x += j.vx
        j.y += j.vy
        j.vy += self.GRAVITY
        if j.y >= self.GROUND_Y:
            j.y = float(self.GROUND_Y)
            j.landed = True
            j.dist = self._compute_flight(j)
            self._on_landing()

    def _on_landing(self) -> None:
        if self.javelin is None:
            return
        dist_m = self.javelin.dist
        self.current_dist = dist_m
        score = int(dist_m * 10)
        if self.super_throw:
            score *= self.SUPER_SCORE_MULT
        self.current_score = score
        self.total_score += score
        if dist_m > self.best_dist:
            self.best_dist = dist_m

        self._spawn_particles(self.javelin.x, self.GROUND_Y, BROWN, 12)

        self.heat = max(0, self.heat - 1)
        self.phase = Phase.RESULT
        self.result_timer = 120

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi)
            speed = self._rng.uniform(0.5, 2.5)
            life = self._rng.randint(10, 20)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=-math.sin(angle) * speed,
                    life=life,
                    color=color,
                )
            )

    def _spawn_match_particles(self, color: int) -> None:
        self._spawn_particles(
            float(self.ATHLETE_X),
            float(self.GROUND_Y) - 8.0,
            color,
            6,
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _next_attempt(self) -> None:
        self.attempt += 1
        if self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        if self.attempt >= self.MAX_ATTEMPTS:
            self.phase = Phase.GAME_OVER
            return
        self._start_run_up()

    def _start_run_up(self) -> None:
        self.phase = Phase.RUN_UP
        self.world_x = 0.0
        self.combo = 0
        self.super_throw = False
        self._last_matched_color = None
        self.zones = [self._spawn_zone()]
        self.zones_spawned = 1
        self.javelin = None
        self.mouse_drag_start = None
        self.throw_power = 0.0
        self.throw_angle = 0.0
        self.current_dist = 0.0
        self.current_score = 0
        self.result_timer = 0

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.attempt = 0
        self.world_x = 0.0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.zones.clear()
        self.javelin = None
        self.particles.clear()
        self.best_dist = 0.0
        self.total_score = 0
        self.super_throw = False
        self.current_dist = 0.0
        self.current_score = 0
        self.mouse_drag_start = None
        self.throw_power = 0.0
        self.throw_angle = 0.0
        self.zone_timer = 0.0
        self.result_timer = 0
        self.zones_spawned = 0
        self._last_matched_color = None

    @staticmethod
    def _make_game() -> Game:
        g = Game.__new__(Game)
        Game.__init__(g)
        g.reset()
        return g

    def check_heat_game_over(self) -> bool:
        if self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return True
        return False

    def try_advance_result(self) -> None:
        if self.result_timer > 0:
            self.result_timer -= 1
            return
        self._next_attempt()


# ── Pyxel App ────────────────────────────────────────────────────────────


class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="JAVELIN SURGE")
        font_path = Path(__file__).with_name("k8x12.bdf")
        try:
            pyxel.load(str(font_path))
        except Exception:
            pass
        self.game = Game()
        self.game.reset()
        self._space_held = False
        self._prev_mouse_pressed = False
        self._screen_shake = 0
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        g._update_particles()

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        match g.phase:
            case Phase.TITLE:
                if pyxel.btnp(pyxel.KEY_RETURN):
                    g.phase = Phase.RUN_UP
                    g._start_run_up()
            case Phase.RUN_UP:
                self._update_run_up()
            case Phase.THROW:
                self._update_throw()
            case Phase.FLIGHT:
                g._update_flight()
            case Phase.RESULT:
                if g.result_timer > 0:
                    g.result_timer -= 1
                if g.result_timer <= 0 and pyxel.btnp(pyxel.KEY_RETURN):
                    g._next_attempt()
            case Phase.GAME_OVER:
                if pyxel.btnp(pyxel.KEY_RETURN):
                    g.reset()

    def _update_run_up(self) -> None:
        g = self.game
        g._update_zones()

        if pyxel.btnp(pyxel.KEY_RETURN):
            matched_color = g._try_match_zone()
            if matched_color is not None:
                g._on_match(matched_color)
                g._spawn_match_particles(matched_color)
                if g.super_throw:
                    g._spawn_match_particles(YELLOW)
            else:
                g._on_miss()
            if g.check_heat_game_over():
                return

        if g.phase == Phase.RUN_UP and g.zones_spawned >= g.zone_target_count and not g.zones:
            g._enter_throw_phase()

    def _update_throw(self) -> None:
        g = self.game
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        just_pressed = pressed and not self._prev_mouse_pressed
        just_released = not pressed and self._prev_mouse_pressed

        if just_pressed and g.mouse_drag_start is None:
            g.mouse_drag_start = (float(mx), float(my))

        if pressed and g.mouse_drag_start is not None:
            sx, sy = g.mouse_drag_start
            dx = float(mx) - sx
            dy = float(my) - sy
            g.throw_power = math.hypot(dx, dy) * 0.05
            g.throw_power = max(0.5, min(g.throw_power, 10.0))
            g.throw_angle = math.atan2(-dy, dx)
            g.throw_angle = max(-0.8, min(g.throw_angle, 0.8))

        if just_released and g.mouse_drag_start is not None:
            if g.throw_power > 0:
                g._throw_javelin(g.throw_angle, g.throw_power)
            g.mouse_drag_start = None

        self._prev_mouse_pressed = pressed

    def draw(self) -> None:
        g = self.game
        pyxel.cls(LIGHT_BLUE)

        match g.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.RUN_UP:
                self._draw_run_up()
            case Phase.THROW:
                self._draw_run_up()
                self._draw_throw_ui()
            case Phase.FLIGHT:
                self._draw_flight()
            case Phase.RESULT:
                self._draw_flight()
                self._draw_result_overlay()
            case Phase.GAME_OVER:
                self._draw_game_over()

        self._draw_particles()
        self._draw_hud()

    def _draw_title(self) -> None:
        pyxel.text(100, 70, "JAVELIN SURGE", WHITE)
        pyxel.text(115, 90, "Color-match", GRAY)
        pyxel.text(102, 100, "Javelin Throw", GRAY)

        pyxel.text(105, 130, "Run-up: SPACE to match colors", WHITE)
        pyxel.text(95, 142, "Same color builds COMBO!", YELLOW)
        pyxel.text(85, 154, "Wrong color or miss -> COMBO reset", GRAY)
        pyxel.text(98, 170, "Throw: Mouse drag & release", WHITE)
        pyxel.text(120, 190, "5 attempts, best wins!", WHITE)

        pyxel.text(122, 218, "Press SPACE to start", YELLOW)

    def _draw_run_up(self) -> None:
        g = self.game
        pyxel.rect(0, g.GROUND_Y, g.SCREEN_W, g.SCREEN_H - g.GROUND_Y, BROWN)

        for z in g.zones:
            sx = int(z.x - g.world_x)
            if sx < -30 or sx > g.SCREEN_W + 10:
                continue
            zy = g.GROUND_Y - 10
            color = z.color if not z.hit else WHITE
            pyxel.rect(sx, zy, z.width, 8, color)
            if z.hit:
                pyxel.text(sx + 2, zy - 8, "HIT!", WHITE)

        pyxel.line(g.THROW_LINE_X, g.GROUND_Y - 30, g.THROW_LINE_X, g.GROUND_Y, WHITE)

        self._draw_athlete(g.ATHLETE_X, g.GROUND_Y - 14)

        if g.super_throw:
            self._draw_super_glow()

    def _draw_athlete(self, x: int, y: int) -> None:
        g = self.game
        head_r = 4
        leg_offset = 3 if int(pyxel.frame_count / 6) % 2 == 0 else -3
        pyxel.circ(x, y - 12, head_r, WHITE)
        pyxel.line(x, y - 8, x, y + 4, WHITE)
        pyxel.line(x, y + 4, x - 4, y + 14, WHITE)
        pyxel.line(x, y + 4, x + 4, y + 14 + leg_offset, WHITE)
        pyxel.line(x, y - 4, x - 5, y + 2, WHITE)
        pyxel.line(x, y - 4, x + 5, y + 2, WHITE)

        if g.super_throw:
            colors = (RED, ORANGE, YELLOW, LIME, CYAN, PURPLE)
            ci = colors[(pyxel.frame_count // 3) % len(colors)]
            pyxel.circb(x, y - 12, head_r + 3, ci)

    def _draw_super_glow(self) -> None:
        colors = (RED, ORANGE, YELLOW, LIME, CYAN, PURPLE)
        ci = colors[(pyxel.frame_count // 3) % len(colors)]
        pyxel.text(120, 5, "SUPER THROW READY!", ci)

    def _draw_throw_ui(self) -> None:
        g = self.game
        tx = g.THROW_LINE_X
        ty = g.GROUND_Y - 14

        if g.mouse_drag_start is not None:
            sx, sy = g.mouse_drag_start
            mx = float(pyxel.mouse_x)
            my = float(pyxel.mouse_y)
            pyxel.line(int(sx), int(sy), int(mx), int(my), YELLOW)
            pyxel.circ(int(sx), int(sy), 3, ORANGE)

            pct = g.throw_power / 10.0
            bar_w = int(pct * 60)
            pyxel.rect(tx - 30, ty - 20, 60, 6, GRAY)
            bar_color = GREEN if pct < 0.5 else (YELLOW if pct < 0.8 else RED)
            pyxel.rect(tx - 30, ty - 20, bar_w, 6, bar_color)

            ang_deg = int(math.degrees(g.throw_angle))
            pyxel.text(tx - 30, ty - 32, f"PWR:{g.throw_power:.1f}", WHITE)
            pyxel.text(tx - 30, ty - 46, f"ANG:{ang_deg}", WHITE)

    def _draw_flight(self) -> None:
        g = self.game
        self._draw_run_up()

        if g.javelin is not None:
            j = g.javelin
            jx = int(j.x - g.world_x)
            jy = int(j.y)
            angle = math.atan2(-j.vy, j.vx) if (j.vx != 0 or j.vy != 0) else 0.0
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            length = 16.0
            tip_x = int(jx + cos_a * length)
            tip_y = int(jy - sin_a * length)
            tail_x = int(jx - cos_a * length)
            tail_y = int(jy + sin_a * length)
            pyxel.line(tail_x, tail_y, tip_x, tip_y, j.color)
            pyxel.circ(tip_x, tip_y, 2, j.color)

            if g.super_throw:
                colors = (RED, ORANGE, YELLOW, LIME, CYAN, PURPLE)
                for i in range(3):
                    ci = colors[(pyxel.frame_count // 2 + i) % len(colors)]
                    ox = int(jx + cos_a * (length + i * 4))
                    oy = int(jy - sin_a * (length + i * 4))
                    pyxel.circ(ox, oy, 2, ci)

        if g.javelin is not None and g.javelin.landed:
            jx = int(g.javelin.x - g.world_x)
            pyxel.tri(jx, g.GROUND_Y - 10, jx - 4, g.GROUND_Y, jx + 4, g.GROUND_Y, RED)

    def _draw_result_overlay(self) -> None:
        g = self.game
        pyxel.rect(60, 80, 200, 80, NAVY)
        pyxel.rectb(60, 80, 200, 80, WHITE)

        pyxel.text(75, 90, f"Distance: {g.current_dist:.1f}m", WHITE)
        pyxel.text(75, 102, f"Score: +{g.current_score}", YELLOW)

        label = "*** SUPER THROW! ***" if g.super_throw else ""
        if label:
            pyxel.text(90, 116, label, ORANGE)

        pyxel.text(75, 130, "Best: {:.1f}m  Total: {}".format(g.best_dist, g.total_score), WHITE)

        if g.result_timer <= 0:
            pyxel.text(80, 146, "Press SPACE to continue", YELLOW)

    def _draw_game_over(self) -> None:
        g = self.game
        pyxel.rect(40, 60, 240, 120, NAVY)
        pyxel.rectb(40, 60, 240, 120, WHITE)

        pyxel.text(120, 75, "GAME OVER", RED)
        pyxel.text(75, 95, f"Best Throw: {g.best_dist:.1f}m", WHITE)
        pyxel.text(75, 110, f"Total Score: {g.total_score}", YELLOW)
        pyxel.text(75, 125, f"Max Combo: {g.max_combo}", WHITE)
        pyxel.text(75, 140, f"Heat: {g.heat}/{g.MAX_HEAT}", RED if g.heat >= g.MAX_HEAT else GRAY)

        pyxel.text(98, 168, "Press SPACE to restart", YELLOW)

    def _draw_hud(self) -> None:
        g = self.game
        if g.phase in (Phase.TITLE, Phase.GAME_OVER):
            return

        pyxel.text(4, 4, f"Attempt: {g.attempt + 1}/{g.MAX_ATTEMPTS}", WHITE)

        combo_color = WHITE
        if g.combo >= 4:
            colors = (RED, ORANGE, YELLOW, LIME, CYAN, PURPLE)
            combo_color = colors[(pyxel.frame_count // 3) % len(colors)]
        elif g.combo >= 2:
            combo_color = YELLOW
        pyxel.text(4, 14, f"COMBO: x{g.combo}", combo_color)

        heat_str = ""
        for i in range(g.MAX_HEAT):
            heat_str += "#" if i < g.heat else "."
        pyxel.text(4, 24, f"HEAT: [{heat_str}]", RED if g.heat >= 3 else WHITE)

    def _draw_particles(self) -> None:
        g = self.game
        for p in g.particles:
            alpha = min(p.life / 15.0, 1.0)
            if alpha < 0.3:
                continue
            px = int(p.x - g.world_x) if g.phase in (Phase.RUN_UP, Phase.FLIGHT) else int(p.x)
            py = int(p.y)
            if 0 <= px < g.SCREEN_W and 0 <= py < g.SCREEN_H:
                pyxel.pset(px, py, p.color)


if __name__ == "__main__":
    App()
