import math
import random
from dataclasses import dataclass
from enum import Enum, auto

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

CRACK_COLORS = [RED, LIME, DARK_BLUE, PURPLE]
SEGMENT_RADII = [30, 54, 78, 102]
BASE_ANGLES = [math.radians(d) for d in (45, 135, 225, 315)]
CENTER_X = 160
CENTER_Y = 120
CLICK_RADIUS = 10
MAX_CRACKS = 6
TIME_LIMIT = 3600
SEGMENT_SIZE = 12
VESSEL_RADIUS = 96


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Segment:
    x: float
    y: float
    color: int
    filled: bool = False


@dataclass
class Crack:
    angle: float
    segments: list[Segment]
    complete: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="KINTSUGI CHAIN", display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    @property
    def super_active(self) -> bool:
        return self.super_timer > 0

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.frame = 0
        self.score = 0
        self.best_score = getattr(self, "best_score", 0)
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.brush_color = CRACK_COLORS[0]
        self.brush_timer = self._cycle_interval()
        self.super_timer = 0
        self.cracks = []
        self.completed_veins = 0
        self.restored_count = 0
        self.next_crack_spawn = 240
        self.particles = []
        self.floats = []
        self.shake = 0
        self.rng = getattr(self, "rng", random.Random())
        self._sfx_enabled = getattr(self, "_sfx_enabled", True)
        for angle in BASE_ANGLES:
            self._spawn_crack(angle)

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.frame // 150)

    def _crack_spawn_interval(self) -> int:
        return max(120, 240 - self.frame // 30)

    def _make_crack(self, angle: float) -> Crack:
        segments = []
        for radius in SEGMENT_RADII:
            x = CENTER_X + radius * math.cos(angle)
            y = CENTER_Y + radius * math.sin(angle)
            color = self.rng.choice(CRACK_COLORS)
            segments.append(Segment(x, y, color))
        return Crack(angle, segments)

    def _spawn_crack(self, angle: float) -> None:
        if len(self.cracks) >= MAX_CRACKS:
            return
        self.cracks.append(self._make_crack(angle))

    def _brush_cycle(self) -> None:
        if self.super_active:
            return
        self.brush_timer -= 1
        if self.brush_timer <= 0:
            idx = CRACK_COLORS.index(self.brush_color)
            self.brush_color = CRACK_COLORS[(idx + 1) % len(CRACK_COLORS)]
            self.brush_timer = self._cycle_interval()

    def _update_crack_spawn(self) -> None:
        if self.frame >= self.next_crack_spawn and len(self.cracks) < MAX_CRACKS:
            self._spawn_crack(self.rng.uniform(0.0, math.tau))
            self.next_crack_spawn = self.frame + self._crack_spawn_interval()

    def _update_heat(self) -> None:
        if self.heat >= 100:
            self.phase = Phase.GAME_OVER
            return
        if not self.super_active:
            self.heat = max(0.0, self.heat - 0.02)

    def _update_timer(self) -> None:
        if self.frame >= TIME_LIMIT:
            self.phase = Phase.GAME_OVER

    def _burst(
        self,
        x: float,
        y: float,
        color: int,
        count: int,
        speed: float,
        life_min: int,
        life_max: int,
    ) -> None:
        for _ in range(count):
            ang = self.rng.uniform(0.0, math.tau)
            mag = self.rng.uniform(0.0, speed)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * mag,
                    math.sin(ang) * mag,
                    self.rng.randint(life_min, life_max),
                    color,
                )
            )

    def _restored_burst(self) -> None:
        for i in range(30):
            ang = self.rng.uniform(0.0, math.tau)
            mag = self.rng.uniform(0.0, 3.0)
            color = YELLOW if i % 2 == 0 else ORANGE
            self.particles.append(
                Particle(
                    CENTER_X,
                    CENTER_Y,
                    math.cos(ang) * mag,
                    math.sin(ang) * mag,
                    self.rng.randint(30, 50),
                    color,
                )
            )

    def _try_fill(self, x: float, y: float) -> None:
        best: Segment | None = None
        best_crack: Crack | None = None
        best_dist = float(CLICK_RADIUS)
        for crack in self.cracks:
            if crack.complete:
                continue
            for seg in crack.segments:
                if seg.filled:
                    continue
                d = math.hypot(seg.x - x, seg.y - y)
                if d <= best_dist:
                    best_dist = d
                    best = seg
                    best_crack = crack
        if best is None or best_crack is None:
            return

        if best.color == self.brush_color or self.super_active:
            best.filled = True
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gain = 10 * self.combo * (3 if self.super_active else 1)
            self.score += gain
            self._burst(best.x, best.y, best.color, 8, 1.5, 20, 30)
            self.floats.append(FloatText(best.x, best.y, f"+{gain}", WHITE, 30))
            if self.combo >= 4:
                self.super_timer = 300
            if self.combo == 4:
                self.floats.append(FloatText(CENTER_X, 40, "SUPER KINTSUGI!", YELLOW, 50))

            bonus = self._check_crack_complete(best_crack)
            if bonus > 0:
                outer = best_crack.segments[-1]
                self._burst(outer.x, outer.y, YELLOW, 16, 2.5, 25, 40)
                self.floats.append(
                    FloatText(CENTER_X, 90, f"GOLD VEIN +{bonus}", YELLOW, 50)
                )
                self.shake = 8
            if self._check_vessel_restored():
                self._restored_burst()
                self.floats.append(
                    FloatText(CENTER_X, 90, "VESSEL RESTORED +500", YELLOW, 60)
                )
                self.shake = 12
        else:
            self.heat += 15
            self.combo = 0
            self.floats.append(FloatText(best.x, best.y, "WRONG!", RED, 30))
            self.shake = 4
            self._burst(best.x, best.y, GRAY, 4, 1.0, 15, 25)

    def _check_crack_complete(self, crack: Crack) -> int:
        if crack.complete:
            return 0
        if all(seg.filled for seg in crack.segments):
            crack.complete = True
            self.completed_veins += 1
            bonus = 50 * self.combo * self.completed_veins
            self.score += bonus
            return bonus
        return 0

    def _check_vessel_restored(self) -> bool:
        if self.cracks and all(c.complete for c in self.cracks):
            self.score += 500
            self.restored_count += 1
            self.completed_veins = 0
            self.cracks = [self._make_crack(a) for a in BASE_ANGLES]
            return True
        return False

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _update_shake(self) -> None:
        if self.shake > 0:
            self.shake -= 1

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self.frame += 1
            self._brush_cycle()
            self._update_crack_spawn()
            self._update_heat()
            if self.phase == Phase.GAME_OVER:
                return
            self._update_timer()
            if self.phase == Phase.GAME_OVER:
                return
            if self.super_timer > 0:
                self.super_timer -= 1
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._try_fill(pyxel.mouse_x, pyxel.mouse_y)
            self._update_particles()
            self._update_floats()
            self._update_shake()
            self.best_score = max(self.best_score, self.score)
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.PLAYING

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        else:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(95, 60, "KINTSUGI CHAIN", WHITE)
        pyxel.text(70, 76, "REPAIR THE BROKEN VESSEL WITH GOLD", GRAY)
        pyxel.text(60, 110, "CLICK matching segments to fill gold", WHITE)
        pyxel.text(72, 122, "COMBO>=4 = SUPER KINTSUGI", WHITE)
        pyxel.text(60, 134, "Complete a crack = gold vein bonus", WHITE)
        pyxel.text(90, 160, "PRESS ENTER TO START", YELLOW)

    def _draw_playing(self) -> None:
        ox = self.rng.randint(-2, 2) if self.shake > 0 else 0
        oy = self.rng.randint(-2, 2) if self.shake > 0 else 0

        pyxel.circ(CENTER_X + ox, CENTER_Y + oy, VESSEL_RADIUS, GRAY)
        pyxel.circb(CENTER_X + ox, CENTER_Y + oy, VESSEL_RADIUS, BROWN)

        for crack in self.cracks:
            if crack.complete:
                outer = crack.segments[-1]
                pyxel.line(
                    CENTER_X + ox,
                    CENTER_Y + oy,
                    int(outer.x) + ox,
                    int(outer.y) + oy,
                    YELLOW,
                )
            for seg in crack.segments:
                sx = int(seg.x) - SEGMENT_SIZE // 2 + ox
                sy = int(seg.y) - SEGMENT_SIZE // 2 + oy
                if seg.filled:
                    pyxel.rect(sx, sy, SEGMENT_SIZE, SEGMENT_SIZE, YELLOW)
                    pyxel.rect(sx + 4, sy + 4, 4, 4, ORANGE)
                else:
                    pyxel.rect(sx, sy, SEGMENT_SIZE, SEGMENT_SIZE, seg.color)

        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color)

        for f in self.floats:
            pyxel.text(int(f.x) + ox, int(f.y) + oy, f.text, f.color)

        self._draw_hud()

        if self.super_active:
            border = CRACK_COLORS[self.frame // 6 % 4]
            pyxel.rectb(0, 0, 320, 240, border)

    def _draw_hud(self) -> None:
        timer_w = max(0, int((TIME_LIMIT - self.frame) / TIME_LIMIT * 304))
        pyxel.rect(8, 4, timer_w, 3, LIME)

        if self.super_active:
            brush_color = CRACK_COLORS[self.frame // 4 % 4]
        else:
            brush_color = self.brush_color
        pyxel.rect(152, 10, 16, 16, brush_color)
        pyxel.text(112, 12, "BRUSH", GRAY)

        pyxel.text(8, 34, f"SCORE {self.score}", WHITE)
        pyxel.text(248, 34, f"COMBO x{self.combo}", WHITE)

        heat_h = int(self.heat / 100 * 200)
        if self.heat < 50:
            heat_color = GREEN
        elif self.heat < 80:
            heat_color = YELLOW
        else:
            heat_color = RED
        pyxel.rect(304, 20, 8, 200, DARK_BLUE)
        pyxel.rect(304, 220 - heat_h, 8, heat_h, heat_color)

    def _draw_game_over(self) -> None:
        reason = "VESSEL SHATTERED" if self.heat >= 100 else "TIME UP"
        pyxel.text(104, 80, reason, RED)
        pyxel.text(112, 100, f"SCORE {self.score}", WHITE)
        pyxel.text(112, 112, f"BEST {self.best_score}", WHITE)
        pyxel.text(84, 140, "PRESS R TO RESTART", YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
