"""098_arrow_chain -- Color-Match Archery Chain Prototype

The most fun moment:
  同じ色の的を連続射抜いてCOMBOを積み重ね、
  SUPER ARROWで遠くの高得点的を一撃で射抜く瞬間

Core loop: Mouse drag-aim-shoot at colored targets.
Same-color hits build COMBO -> COMBO>=4 triggers SUPER (3x score, all colors match).
Misses build HEAT; HEAT>=5 = game over. 60-second time limit.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
COLORS = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES = ("RED", "GREEN", "BLUE", "YELLOW")
GAME_TIME = 60 * 30
MAX_HEAT = 5
SUPER_COMBO = 4
SUPER_DURATION = 5 * 30
MAX_TARGETS = 5
GRAVITY = 0.15
BOW_X = 160.0
BOW_Y = 220.0
MIN_ALIVE_TARGETS = 3

# pyxel palette ints
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

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Target:
    x: float
    y: float
    depth: float  # 0.3-1.0  (1.0 = closest / largest)
    color: int  # 0-3 index into COLORS
    radius: int
    score_base: int
    alive: bool = True
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class Arrow:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    alive: bool = True
    trail: list[tuple[float, float]] = field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="098 Arrow Chain", display_scale=2)
        if FONT_PATH.exists():
            pyxel.load(str(FONT_PATH))
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    # -- state initialisation (callable from headless tests) ---------------

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.timer: int = GAME_TIME
        self.arrow_color: int = 0
        self.targets: list[Target] = []
        self.arrow: Arrow | None = None
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.super_timer: int = 0
        self.aiming: bool = False
        self.aim_start_x: float = 0.0
        self.aim_start_y: float = 0.0
        self._rng: random.Random = random.Random()

    def reset(self) -> None:
        self._init_state()

    # -- update ------------------------------------------------------------

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        self._handle_input()

        if self.arrow is not None and self.arrow.alive:
            self._update_arrow()

        self._update_targets()

        alive_count = sum(1 for t in self.targets if t.alive)
        if alive_count < MIN_ALIVE_TARGETS:
            self._spawn_targets(MAX_TARGETS - alive_count)
        # Cap total alive
        alive = [t for t in self.targets if t.alive]
        if len(alive) > MAX_TARGETS:
            for t in alive[MAX_TARGETS:]:
                t.alive = False

        self._update_particles()
        self._update_floating_texts()

    # -- input -------------------------------------------------------------

    def _handle_input(self) -> None:
        if self.arrow is not None and self.arrow.alive:
            return

        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.aiming = True
            self.aim_start_x = float(mx)
            self.aim_start_y = float(my)

        if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT) and self.aiming:
            self.aiming = False
            release_x = float(mx)
            release_y = float(my)
            power_x = (self.aim_start_x - release_x) * 0.08
            power_y = (self.aim_start_y - release_y) * 0.08
            max_power = 4.0
            power_x = max(-max_power, min(max_power, power_x))
            power_y = max(-max_power, min(max_power, power_y))
            self._shoot_arrow(power_x, power_y)

    # -- targets -----------------------------------------------------------

    def _spawn_targets(self, count: int) -> None:
        for _ in range(count):
            depth = self._rng.uniform(0.3, 1.0)
            radius = int(8 + depth * 12)  # 8 .. 20
            score_base = int(50 + depth * 250)  # 50 .. 300
            margin = radius + 5
            x = self._rng.uniform(float(margin), float(SCREEN_W - margin))
            base_y = 40.0 + (1.0 - depth) * 120.0
            y = base_y + self._rng.uniform(-20.0, 20.0)
            color = self._rng.randint(0, 3)
            vx = self._rng.uniform(-0.3, 0.3)
            vy = self._rng.uniform(-0.2, 0.2)
            self.targets.append(
                Target(
                    x=x,
                    y=y,
                    depth=depth,
                    color=color,
                    radius=radius,
                    score_base=score_base,
                    vx=vx,
                    vy=vy,
                )
            )

    def _update_targets(self) -> None:
        for target in self.targets:
            if not target.alive:
                continue
            target.x += target.vx
            target.y += target.vy
            if target.x - target.radius < 0:
                target.x = float(target.radius)
                target.vx = abs(target.vx)
            elif target.x + target.radius > SCREEN_W:
                target.x = float(SCREEN_W - target.radius)
                target.vx = -abs(target.vx)
            if target.y - target.radius < 20:
                target.y = 20.0 + float(target.radius)
                target.vy = abs(target.vy)
            elif target.y + target.radius > BOW_Y - 10:
                target.y = BOW_Y - 10.0 - float(target.radius)
                target.vy = -abs(target.vy)

    # -- arrow -------------------------------------------------------------

    def _shoot_arrow(self, power_x: float, power_y: float) -> None:
        self.arrow = Arrow(
            x=BOW_X,
            y=BOW_Y,
            vx=power_x,
            vy=power_y,
            color=self.arrow_color,
        )

    def _update_arrow(self) -> None:
        if self.arrow is None:
            return
        a = self.arrow
        a.trail.append((a.x, a.y))
        if len(a.trail) > 20:
            a.trail.pop(0)

        a.vy += GRAVITY
        a.x += a.vx
        a.y += a.vy

        # off-screen
        if a.x < -10 or a.x > SCREEN_W + 10 or a.y < -10 or a.y > SCREEN_H + 10:
            a.alive = False
            self._handle_miss()
            return

        # collision
        hit_target: Target | None = None
        best_depth = -1.0
        for target in self.targets:
            if not target.alive:
                continue
            if self._check_target_hit(a, target) and target.depth > best_depth:
                best_depth = target.depth
                hit_target = target

        if hit_target is not None:
            a.alive = False
            hit_target.alive = False
            self._handle_hit(hit_target)

    def _check_target_hit(self, arrow: Arrow, target: Target) -> bool:
        dx = arrow.x - target.x
        dy = arrow.y - target.y
        return math.hypot(dx, dy) < target.radius + 3

    # -- scoring / combo ---------------------------------------------------

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _handle_hit(self, target: Target) -> None:
        same_color = self._is_super() or (target.color == self.arrow_color)

        if same_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            base = target.score_base
            bonus = self.combo * 50
            mult = 3 if self._is_super() else 1
            gained = (base + bonus) * mult
            self.score += gained
            self.arrow_color = target.color
            self._spawn_hit_particles(target.x, target.y, COLORS[target.color])
            txt_color = YELLOW if self._is_super() else WHITE
            self.floating_texts.append(
                FloatingText(target.x, target.y, f"+{gained}", txt_color, 30)
            )
            if self.combo >= 2:
                self.floating_texts.append(
                    FloatingText(target.x, target.y - 10, f"{self.combo}COMBO", ORANGE, 25)
                )
            if self.combo >= SUPER_COMBO and self.super_timer <= 0:
                self._activate_super()
        else:
            self.combo = 0
            self.heat += 1
            self.arrow_color = target.color
            self.score += 10
            self.floating_texts.append(
                FloatingText(target.x, target.y, "WRONG", RED, 25)
            )
            self._spawn_hit_particles(target.x, target.y, GRAY)

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        # purge dead
        self.targets = [t for t in self.targets if t.alive]

    def _handle_miss(self) -> None:
        self.heat += 1
        self.combo = 0
        self.floating_texts.append(
            FloatingText(BOW_X, BOW_Y - 15, "MISS", RED, 25)
        )
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.floating_texts.append(
            FloatingText(SCREEN_W / 2, SCREEN_H / 2, "SUPER!", YELLOW, 60)
        )

    # -- particles & floating texts ----------------------------------------

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        count = 20 if self._is_super() else 12
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            p_col = color
            if self._is_super():
                p_col = COLORS[self._rng.randint(0, 3)]
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=p_col,
                    life=self._rng.randint(15, 30),
                    max_life=30,
                )
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

    # -- draw --------------------------------------------------------------

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_sky_ground(self) -> None:
        for i in range(SCREEN_H):
            c = NAVY if i < SCREEN_H // 2 else DARK_BLUE
            pyxel.line(0, i, SCREEN_W, i, c)
        pyxel.rect(0, int(BOW_Y + 5), SCREEN_W, SCREEN_H - int(BOW_Y) - 5, BROWN)

    def _draw_title(self) -> None:
        self._draw_sky_ground()
        title = "098 Arrow Chain"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 40, title, WHITE)
        sub = "Color Archery"
        sw = len(sub) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 55, sub, LIME)

        lines = [
            "Click + Drag = Aim & Power",
            "Release = Shoot",
            "Same Color hit -> COMBO -> SUPER!",
            "SUPER at 4+ COMBO: 3x score!",
            "HEAT on Miss / Wrong hit",
            "HEAT >= 5 = Game Over",
            "",
            "Press SPACE or ENTER to Start",
        ]
        for i, ln in enumerate(lines):
            pyxel.text(20, 80 + i * 11, ln, GRAY)

        for i, col in enumerate(COLORS):
            pyxel.circ(70 + i * 50, 200, 8, col)
            pyxel.circb(70 + i * 50, 200, 8, WHITE)

    def _draw_playing(self) -> None:
        self._draw_sky_ground()

        # targets
        for t in self.targets:
            if not t.alive:
                continue
            col = COLORS[t.color]
            tx, ty = int(t.x), int(t.y)
            pyxel.circ(tx + 1, ty + 1, t.radius, BLACK)
            pyxel.circ(tx, ty, t.radius, col)
            if self._is_super():
                pyxel.circb(tx, ty, t.radius, YELLOW)
                pyxel.circb(tx, ty, t.radius - 2, YELLOW)
            else:
                pyxel.circb(tx, ty, t.radius, WHITE)
                pyxel.circb(tx, ty, t.radius - 3, BLACK)

        # aim line + trajectory preview
        if self.aiming:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - BOW_X
            dy = my - BOW_Y
            dist = math.hypot(dx, dy)
            if dist > 0:
                steps = int(dist / 4)
                for i in range(0, steps, 2):
                    t = i / steps
                    px = BOW_X + dx * t
                    py_ = BOW_Y + dy * t
                    pyxel.pset(int(px), int(py_), LIGHT_BLUE)
            # preview
            power_x = (self.aim_start_x - mx) * 0.08
            power_y = (self.aim_start_y - my) * 0.08
            max_power = 4.0
            power_x = max(-max_power, min(max_power, power_x))
            power_y = max(-max_power, min(max_power, power_y))
            px_v = float(BOW_X)
            py_v = float(BOW_Y)
            pvx = power_x
            pvy = power_y
            for _ in range(20):
                px_v += pvx
                py_v += pvy
                pvy += GRAVITY
                if 0 <= px_v < SCREEN_W and 0 <= py_v < SCREEN_H:
                    pyxel.pset(int(px_v), int(py_v), LIME)

        # flying arrow
        if self.arrow is not None and self.arrow.alive:
            a = self.arrow
            arrow_col = YELLOW if self._is_super() else COLORS[a.color]
            for i, (tx, ty) in enumerate(a.trail):
                alpha = 2 + int((i / max(len(a.trail), 1)) * 6)
                _ = alpha
                pyxel.pset(int(tx), int(ty), arrow_col)
            if len(a.trail) >= 2:
                px_v0, py_v0 = a.trail[-1]
                pyxel.line(int(px_v0), int(py_v0), int(a.x), int(a.y), arrow_col)
            pyxel.circ(int(a.x), int(a.y), 2, arrow_col)

        # bow
        bow_col = COLORS[self.arrow_color]
        pyxel.line(int(BOW_X - 6), int(BOW_Y), int(BOW_X), int(BOW_Y - 12), bow_col)
        pyxel.line(int(BOW_X + 6), int(BOW_Y), int(BOW_X), int(BOW_Y - 12), bow_col)
        pyxel.line(int(BOW_X - 5), int(BOW_Y - 2), int(BOW_X + 5), int(BOW_Y - 2), WHITE)
        pyxel.rect(int(BOW_X - 1), int(BOW_Y - 8), 2, 8, bow_col)

        # particles
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            c = p.color if alpha > 0.5 else GRAY
            pyxel.pset(int(p.x), int(p.y), c)

        # floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            c = ft.color if alpha > 0.4 else GRAY
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, c)

        # --- UI ---
        # HEAT bar
        pyxel.rect(5, 5, 100, 10, DARK_BLUE)
        hw = int(100 * self.heat / MAX_HEAT)
        hc = GREEN if self.heat < 3 else (ORANGE if self.heat < 5 else RED)
        pyxel.rect(5, 5, hw, 10, hc)
        pyxel.rectb(5, 5, 100, 10, WHITE)
        pyxel.text(110, 6, "HEAT", GRAY)

        # COMBO
        if self.combo > 0:
            ctxt = f"COMBO x{self.combo}"
            cc = YELLOW if self._is_super() else (ORANGE if self.combo >= 3 else WHITE)
            pyxel.text(SCREEN_W // 2 - 25, 5, ctxt, cc)

        # SUPER timer
        if self._is_super():
            ssec = self.super_timer // 30 + 1
            pyxel.text(SCREEN_W // 2 - 20, 18, f"SUPER {ssec}s", YELLOW)

        # score
        pyxel.text(SCREEN_W - 75, 5, f"SCORE:{self.score}", WHITE)

        # timer
        tsec = self.timer // 30
        tc = WHITE if tsec > 10 else RED
        pyxel.text(SCREEN_W - 75, 18, f"TIME:{tsec}", tc)

        # max combo
        pyxel.text(SCREEN_W - 75, 31, f"BEST:{self.max_combo}", GRAY)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        go_text = "GAME OVER"
        gw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - gw // 2, 50, go_text, RED)

        def _center_text(y: int, text: str, color: int) -> None:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)

        _center_text(85, f"SCORE: {self.score}", WHITE)
        _center_text(100, f"MAX COMBO: {self.max_combo}", ORANGE)
        _center_text(115, f"HEAT: {self.heat}/{MAX_HEAT}", GRAY)
        super_reached = "YES" if self.max_combo >= SUPER_COMBO else "NO"
        _center_text(130, f"SUPER: {super_reached}", YELLOW)
        _center_text(170, "SPACE or ENTER: Retry", GRAY)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
