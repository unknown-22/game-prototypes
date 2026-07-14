"""FRISBEE CHAIN -- Top-down disc golf color-match COMBO chain game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# ── Constants ──
WIDTH = 320
HEIGHT = 240

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

DISC_COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
RAINBOW_COLORS = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

DISC_START_X = 160
DISC_START_Y = 200
DISC_RADIUS = 8

BASKET_RADIUS = 16
BASKET_MIN_X = 40
BASKET_MAX_X = 280
BASKET_MIN_Y = 30
BASKET_MAX_Y = 150

STAMINA_MAX = 100.0
STAMINA_COST = 20.0
STAMINA_RECHARGE = 0.05
MIN_STAMINA_FULL_POWER = 20.0

MAX_HEAT = 100.0
HEAT_MISMATCH = 15.0
HEAT_MISS = 10.0
HEAT_DECAY = 0.02

MAX_POWER = 6.0
GRAVITY = 0.15
POWER_SCALE = 10.0
MIN_DRAG_DIST = 10.0

GAME_DURATION = 3600
SUPER_DURATION = 300
SUPER_COMBO_THRESHOLD = 4

COLOR_CYCLE = 90
SCORING_DURATION = 80

MAX_GHOST_POINTS = 40


# ── Phase Enum ──
class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    SCORING = auto()
    GAME_OVER = auto()


# ── Data Classes ──
@dataclass
class Basket:
    x: float
    y: float
    color: int


@dataclass
class Disc:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = 0
    active: bool = False
    scored: bool = False
    trail: list[tuple[float, float]] = field(default_factory=list)


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


@dataclass
class GhostTrail:
    x: float
    y: float
    life: int
    color: int


# ── Game ──
class Game:
    phase: Phase
    score: int
    combo: int
    max_combo: int
    stamina: float
    heat: float
    timer: int
    disc: Disc | None
    basket: Basket | None
    disc_color: int
    color_timer: int
    super_timer: int
    aim_start_x: float
    aim_start_y: float
    dragging: bool
    shake_frames: int
    shake_intensity: int
    scoring_timer: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    ghost_trails: list[GhostTrail]
    best_trail: list[tuple[float, float]]
    best_score: int
    rng: random.Random

    def __init__(self) -> None:
        self.rng = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.stamina = STAMINA_MAX
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.disc = None
        self.basket = None
        self.disc_color = 0
        self.color_timer = COLOR_CYCLE
        self.super_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.dragging = False
        self.shake_frames = 0
        self.shake_intensity = 0
        self.scoring_timer = 0
        self.particles = []
        self.floating_texts = []
        self.ghost_trails = []
        self.best_trail = []
        self.best_score = 0

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.stamina = STAMINA_MAX
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.disc = None
        self.basket = None
        self.disc_color = 0
        self.color_timer = COLOR_CYCLE
        self.super_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.dragging = False
        self.shake_frames = 0
        self.shake_intensity = 0
        self.scoring_timer = 0
        self.particles = []
        self.floating_texts = []
        self.ghost_trails = []
        self.best_trail = []
        self.best_score = 0

    def _start_game(self) -> None:
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.stamina = STAMINA_MAX
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.dragging = False
        self.shake_frames = 0
        self.shake_intensity = 0
        self.scoring_timer = 0
        self.disc = None
        self.particles = []
        self.floating_texts = []
        self.ghost_trails = []
        self.best_trail = []
        self.disc_color = 0
        self.color_timer = COLOR_CYCLE
        self._spawn_basket()

    def _spawn_basket(self) -> None:
        x = self.rng.uniform(BASKET_MIN_X, BASKET_MAX_X)
        y = self.rng.uniform(BASKET_MIN_Y, BASKET_MAX_Y)
        color = DISC_COLORS[self.rng.randint(0, 3)]
        self.basket = Basket(x=x, y=y, color=color)

    # ── Throw ──
    def _launch_disc(self, power_x: float, power_y: float) -> None:
        dist = math.hypot(power_x, power_y)
        if dist < MIN_DRAG_DIST:
            return
        raw_power = min(dist / POWER_SCALE, 1.0)

        stamina_factor = 1.0
        if self.stamina < STAMINA_COST:
            stamina_factor = self.stamina / STAMINA_MAX
        self.stamina = max(0.0, self.stamina - STAMINA_COST)

        speed = raw_power * MAX_POWER * stamina_factor
        if speed < 0.1:
            return

        angle = math.atan2(power_y, power_x)
        self.disc = Disc(
            x=float(DISC_START_X),
            y=float(DISC_START_Y),
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            color=self.disc_color,
            active=True,
            scored=False,
        )
        self.phase = Phase.FLYING

    # ── Physics ──
    def _update_disc_flight(self) -> None:
        if self.disc is None or not self.disc.active:
            return
        d = self.disc
        d.trail.append((d.x, d.y))
        d.x += d.vx
        d.y += d.vy
        d.vy += GRAVITY

    def _check_landing(self) -> bool:
        if self.disc is None or not self.disc.active:
            return False
        d = self.disc
        if d.y > HEIGHT or d.x < -20 or d.x > WIDTH + 20:
            return True
        if self.basket is not None:
            dist = math.hypot(d.x - self.basket.x, d.y - self.basket.y)
            if dist <= BASKET_RADIUS:
                return True
        return False

    def _resolve_score(self) -> None:
        if self.disc is None or self.basket is None:
            return
        d = self.disc
        b = self.basket

        is_hit = math.hypot(d.x - b.x, d.y - b.y) <= BASKET_RADIUS
        is_super = self.super_timer > 0

        if is_hit:
            is_match = is_super or (d.color == b.color)
            if is_match:
                self.combo += 1
                mult = 3.0 if is_super else 1.0
                gained = int(100 * self.combo * mult)
                self.score += gained
                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                if self.combo >= SUPER_COMBO_THRESHOLD and not is_super:
                    self._activate_super()

                pcolor = (
                    RAINBOW_COLORS[self.combo % len(RAINBOW_COLORS)]
                    if is_super
                    else b.color
                )
                pcount = 25 if is_super else 15
                self._spawn_particles(b.x, b.y, pcolor, pcount)

                self.floating_texts.append(
                    FloatingText(b.x, b.y - 8, f"+{gained}", pcolor, 40)
                )
                if self.combo > 1:
                    self.floating_texts.append(
                        FloatingText(b.x, b.y - 20, f"COMBO x{self.combo}", YELLOW, 40)
                    )

                if d.trail:
                    self._save_best_trail(d.trail)
            else:
                self.combo = 0
                self.heat = min(MAX_HEAT, self.heat + HEAT_MISMATCH)
                self.shake_frames = 10
                self.shake_intensity = 3
                self._spawn_particles(b.x, b.y, GRAY, 8)
                self.floating_texts.append(
                    FloatingText(b.x, b.y - 8, "WRONG!", ORANGE, 40)
                )
        else:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + HEAT_MISS)
            mx = max(0.0, min(float(WIDTH), d.x))
            my = max(0.0, min(float(HEIGHT), d.y))
            self._spawn_particles(mx, my, GRAY, 8)
            self.floating_texts.append(
                FloatingText(mx, my - 4, "MISS", GRAY, 40)
            )

        d.active = False
        self.scoring_timer = SCORING_DURATION
        self.phase = Phase.SCORING

    # ── Super ──
    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = 15
        self.shake_intensity = 4
        for _ in range(20):
            c = RAINBOW_COLORS[self.rng.randint(0, len(RAINBOW_COLORS) - 1)]
            self.particles.append(
                Particle(
                    x=float(DISC_START_X) + self.rng.uniform(-10, 10),
                    y=float(DISC_START_Y) + self.rng.uniform(-10, 10),
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-3, -1),
                    life=25,
                    color=c,
                )
            )
        self.floating_texts.append(
            FloatingText(
                float(DISC_START_X), float(DISC_START_Y) - 30,
                "SUPER DISC!", PINK, 60,
            )
        )

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.combo = 0

    # ── Timers ──
    def _update_timers(self) -> None:
        if self.timer > 0:
            self.timer -= 1

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = COLOR_CYCLE
            self.disc_color = (self.disc_color + 1) % 4

        self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_RECHARGE)
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Particles ──
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.5, 2.0)
            life = 20 + self.rng.randint(0, 10)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles[:] = [p for p in self.particles if p.life > 0]

    # ── Floating Texts ──
    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Ghost Trails ──
    def _save_best_trail(self, trail: list[tuple[float, float]]) -> None:
        if not trail:
            return
        t = list(trail)
        if len(t) > MAX_GHOST_POINTS:
            step = len(t) / MAX_GHOST_POINTS
            t = [t[int(i * step)] for i in range(MAX_GHOST_POINTS)]
        self.best_trail = t

    def _update_ghost_trails(self) -> None:
        for g in self.ghost_trails:
            g.life -= 1
        self.ghost_trails[:] = [g for g in self.ghost_trails if g.life > 0]

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ── Update ──
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
            ):
                self._start_game()

        elif self.phase == Phase.AIMING:
            self._update_timers()
            self._update_super_timer()
            self._update_particles()
            self._update_floating_texts()

            if self.shake_frames > 0:
                self.shake_frames -= 1
                if self.shake_frames == 0:
                    self.shake_intensity = 0

            if self.heat >= MAX_HEAT or self.timer <= 0:
                self._end_game()
                return

            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.dragging = True
                self.aim_start_x = float(mx)
                self.aim_start_y = float(my)

            if self.dragging and pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                self.dragging = False
                dx = float(mx) - self.aim_start_x
                dy = float(my) - self.aim_start_y
                self._launch_disc(dx, dy)

        elif self.phase == Phase.FLYING:
            self._update_timers()
            self._update_super_timer()
            self._update_disc_flight()
            self._update_particles()
            self._update_floating_texts()

            if pyxel.frame_count % 3 == 0:
                if self.disc is not None and self.disc.active:
                    self.ghost_trails.append(
                        GhostTrail(
                            x=self.disc.x,
                            y=self.disc.y,
                            life=20,
                            color=self.disc.color,
                        )
                    )
            self._update_ghost_trails()

            if self._check_landing():
                self._resolve_score()

        elif self.phase == Phase.SCORING:
            self._update_timers()
            self._update_super_timer()
            self._update_particles()
            self._update_floating_texts()
            self._update_ghost_trails()

            if self.shake_frames > 0:
                self.shake_frames -= 1
                if self.shake_frames == 0:
                    self.shake_intensity = 0

            self.scoring_timer -= 1
            if self.scoring_timer <= 0:
                self.disc = None
                self.ghost_trails.clear()
                if self.timer <= 0 or self.heat >= MAX_HEAT:
                    self._end_game()
                else:
                    self._spawn_basket()
                    self.phase = Phase.AIMING

        elif self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
            ):
                self._start_game()

    # ── Draw ──
    def draw(self) -> None:
        pyxel.cls(NAVY)

        # Sky gradient / field
        pyxel.rect(0, 120, WIDTH, HEIGHT - 120, GREEN)
        for x in range(0, WIDTH, 8):
            pyxel.pset(x, HEIGHT - 8, BROWN)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_game()

        if self.shake_frames > 0:
            sx = self.rng.randint(-self.shake_intensity, self.shake_intensity)
            sy = self.rng.randint(-self.shake_intensity, self.shake_intensity)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.super_timer > 0:
            bc = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
            pyxel.rectb(0, 0, WIDTH, HEIGHT, bc)

    def _draw_title(self) -> None:
        self._text_center(50, "FRISBEE CHAIN", WHITE)
        self._text_center(75, "Disc Golf COMBO", GRAY)
        self._text_center(105, "Click & drag to aim / throw", WHITE)
        self._text_center(120, "Match disc color with basket = COMBO", YELLOW)
        self._text_center(135, "Combo x4 = SUPER DISC! (3x)", PINK)
        self._text_center(150, "Watch STAMINA (green bar)", GREEN)
        self._text_center(165, "Avoid HEAT (red bar)", ORANGE)
        if self.best_score > 0:
            self._text_center(185, f"Best Score: {self.best_score}", WHITE)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(210, "Click to Start", YELLOW)

    def _draw_game(self) -> None:
        self._draw_basket()
        self._draw_ghost_trails()
        self._draw_disc()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_aim_indicator()
        self._draw_hud()

    def _draw_basket(self) -> None:
        if self.basket is None:
            return
        b = self.basket
        bcolor = b.color
        if self.super_timer > 0:
            bcolor = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]

        bx, by = int(b.x), int(b.y)

        # Chains (vertical lines with top ring)
        chain_top = by - 24
        chain_bottom = by - 8
        for dx in (-8, -5, -2, 1, 4, 7):
            pyxel.line(bx + dx, chain_top, bx + dx, chain_bottom, GRAY)
        pyxel.line(bx - 8, chain_top, bx + 8, chain_top, GRAY)
        pyxel.line(bx - 8, chain_bottom, bx + 8, chain_bottom, GRAY)
        pyxel.line(bx - 6, by - 16, bx + 6, by - 16, GRAY)

        # Basket rim
        pyxel.circb(bx, by, 14, WHITE)
        pyxel.circb(bx, by, 12, bcolor)

        # Crosshair
        pyxel.line(bx - 4, by, bx + 4, by, WHITE)
        pyxel.line(bx, by - 4, bx, by + 4, WHITE)
        pyxel.pset(bx, by, WHITE)

    def _draw_disc(self) -> None:
        if self.disc is None or not self.disc.active:
            return
        d = self.disc
        dcolor = d.color
        if self.super_timer > 0:
            dcolor = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
        pyxel.circ(int(d.x), int(d.y), DISC_RADIUS, dcolor)
        pyxel.circb(int(d.x), int(d.y), DISC_RADIUS, WHITE)
        pyxel.pset(int(d.x), int(d.y), WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pcolor = p.color if p.life > 5 else GRAY
            pyxel.pset(int(p.x), int(p.y), pcolor)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40.0
            tcolor = ft.color if alpha > 0.5 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, tcolor)

    def _draw_ghost_trails(self) -> None:
        for px, py in self.best_trail:
            pyxel.pset(int(px), int(py), GRAY)
        for g in self.ghost_trails:
            alpha = g.life / 20.0
            if alpha > 0.2:
                pyxel.pset(int(g.x), int(g.y), g.color)

    def _draw_aim_indicator(self) -> None:
        # Disc at rest position (during aiming)
        if self.disc is not None and self.disc.active:
            return

        dcolor = DISC_COLORS[self.disc_color]
        if self.super_timer > 0:
            dcolor = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]

        pyxel.circ(DISC_START_X, DISC_START_Y, DISC_RADIUS, dcolor)
        pyxel.circb(DISC_START_X, DISC_START_Y, DISC_RADIUS, WHITE)
        pyxel.pset(DISC_START_X, DISC_START_Y, WHITE)

        if self.phase == Phase.AIMING and self.dragging:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            aim_dx = mx - DISC_START_X
            aim_dy = my - DISC_START_Y
            aim_dist = math.hypot(aim_dx, aim_dy)

            if aim_dist > 2:
                steps = min(20, int(aim_dist / 6))
                for i in range(steps):
                    t = (i + 1) / steps
                    px = DISC_START_X + aim_dx * t
                    py = DISC_START_Y + aim_dy * t
                    if i % 2 == 0:
                        pyxel.pset(int(px), int(py), WHITE)

            # Power ring
            drag_dist = math.hypot(
                mx - self.aim_start_x, my - self.aim_start_y,
            )
            power_ring = min(20, int(drag_dist / 3))
            if power_ring > 0:
                pyxel.circb(
                    DISC_START_X, DISC_START_Y,
                    DISC_RADIUS + 2 + power_ring, YELLOW,
                )

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 3, f"SCORE: {self.score}", WHITE)

        # Combo
        ccolor = YELLOW
        if self.combo >= SUPER_COMBO_THRESHOLD or self.super_timer > 0:
            ccolor = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
        pyxel.text(130, 3, f"COMBO: x{self.combo}", ccolor)

        # Timer
        sec = (self.timer + 59) // 60
        tcolor = WHITE if sec > 10 else RED
        pyxel.text(260, 3, f"TIME:{sec:02d}", tcolor)

        # Super timer
        if self.super_timer > 0:
            stext = f"SUPER! {self.super_timer // 60}s"
            self._text_center(20, stext, PINK)

        # Stamina bar (bottom-left)
        bar_x = 4
        bar_w = 10
        bar_h = 60
        bar_y = HEIGHT - bar_h - 6
        fill = int(bar_h * self.stamina / STAMINA_MAX)
        if self.stamina > 50:
            sc = GREEN
        elif self.stamina > 20:
            sc = YELLOW
        else:
            sc = RED
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        pyxel.rect(bar_x, bar_y + bar_h - fill, bar_w, fill, sc)
        pyxel.text(bar_x, bar_y + bar_h + 4, "STA", WHITE)

        # Heat bar (bottom-left, next to stamina)
        hx = 18
        pyxel.rect(hx, bar_y, bar_w, bar_h, GRAY)
        hfill = int(bar_h * self.heat / MAX_HEAT)
        if self.heat < 40:
            hc = GREEN
        elif self.heat < 70:
            hc = ORANGE
        else:
            hc = RED
        pyxel.rect(hx, bar_y + bar_h - hfill, bar_w, hfill, hc)
        pyxel.text(hx, bar_y + bar_h + 4, "HEAT", WHITE)

        # Disc color indicator (top-right)
        pyxel.rect(WIDTH - 16, 18, 10, 10, DISC_COLORS[self.disc_color])
        pyxel.rectb(WIDTH - 16, 18, 10, 10, WHITE)

    def _draw_game_over(self) -> None:
        self._text_center(60, "GAME OVER", RED)
        self._text_center(95, f"Score: {self.score}", WHITE)
        self._text_center(115, f"Max COMBO: x{self.max_combo}", YELLOW)
        self._text_center(135, f"Best Score: {self.best_score}", WHITE)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(175, "Click to Retry", GRAY)

    # ── Utility ──
    def _text_center(self, y: int, text: str, color: int) -> None:
        x = (WIDTH - len(text) * pyxel.FONT_WIDTH) // 2
        pyxel.text(x, y, text, color)


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="FRISBEE CHAIN")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
