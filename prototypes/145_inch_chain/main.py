"""INCH CHAIN - An inchworm eats colored dots to build combos."""
import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---- Constants ----
SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 200
WORM_Y = 190
NUM_SEGMENTS = 7
SUPER_DURATION = 300  # 5 seconds at 60fps
LUNGE_DURATION = 10  # frames of speed boost after releasing SPACE
EAT_RADIUS = 10
SUPER_COLLECT_RADIUS = 60

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

DOT_COLORS = [RED, GREEN, DARK_BLUE, YELLOW]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SUPER = auto()
    GAME_OVER = auto()


@dataclass
class Segment:
    x: float
    y: float
    angle: float = 0.0


@dataclass
class Dot:
    x: float
    y: float
    color: int
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


@dataclass
class GhostPoint:
    x: float
    y: float


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="INCH CHAIN", fps=60, display_scale=2)
        self._rng: random.Random
        self.phase: Phase
        self.segments: list[Segment]
        self.dots: list[Dot]
        self.combo: int
        self.max_combo: int
        self.score: int
        self.heat: float
        self.super_timer: int
        self.particles: list[Particle]
        self.floating_texts: list[FloatingText]
        self.ghost_points: list[GhostPoint]
        self.best_ghost: list[GhostPoint]
        self.ground_scroll: float
        self.frame: int
        self._last_color: int
        self._contract_amount: float
        self._lunge_frames: int
        self._best_score: int
        self._spawn_timer: int
        self._wave_phase: float
        self._prev_space: bool
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.TITLE
        self.segments = [Segment(x=160.0 - i * 8.0, y=WORM_Y) for i in range(NUM_SEGMENTS)]
        self.dots = []
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.particles = []
        self.floating_texts = []
        self.ghost_points = []
        self.best_ghost = []
        self.ground_scroll = 0.0
        self.frame = 0
        self._last_color = -1
        self._contract_amount = 0.0
        self._lunge_frames = 0
        self._best_score = 0
        self._spawn_timer = 0
        self._wave_phase = 0.0
        self._prev_space = False

    # ---- Testable Core Methods ----

    def _spawn_dot(self) -> Dot:
        color_idx = self._rng.randint(0, 3)
        x = SCREEN_W + self._rng.uniform(10, 50)
        y = GROUND_Y - self._rng.uniform(0, 14)
        return Dot(x=x, y=y, color=color_idx)

    def _speed_for_score(self) -> float:
        return 1.5 + self.score / 1000.0 * 0.5

    def _get_current_speed(self) -> float:
        speed = self._speed_for_score()
        if self._contract_amount > 0.3:
            speed *= 0.3
        elif self._lunge_frames > 0:
            speed *= 2.5
        return speed

    def _update_worm(self) -> None:
        speed = self._get_current_speed()
        self.ground_scroll += speed

        head = self.segments[0]
        head.x += speed
        if head.x < 0:
            head.x = 0
        if head.x > SCREEN_W:
            head.x = SCREEN_W

        self._wave_phase = self.frame * 0.1
        for i, seg in enumerate(self.segments):
            seg.angle = math.sin(self._wave_phase + i * 1.2) * 3
            seg.y = WORM_Y + seg.angle

        spacing = 12.0 - self._contract_amount * 8.0
        for i in range(1, len(self.segments)):
            prev = self.segments[i - 1]
            curr = self.segments[i]
            dx = prev.x - curr.x
            dy = prev.y - curr.y
            dist = math.hypot(dx, dy)
            if dist > spacing:
                ratio = (dist - spacing) / dist
                curr.x += dx * ratio
                curr.y += dy * ratio

    def _update_dots(self) -> None:
        for dot in self.dots:
            dot.x -= 0.5
        self.dots = [d for d in self.dots if d.alive and d.x > -10]

    def _eat_dot(self, dot: Dot) -> tuple[int, int, bool]:
        is_super_triggered = False
        if self.super_timer > 0:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            score_add = (10 + self.combo * 5) * 3
            heat_add = 0
        else:
            if self._last_color < 0:
                self.combo = 1
                score_add = 10 + self.combo * 5
                heat_add = 0
            elif dot.color == self._last_color:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                score_add = 10 + self.combo * 5
                heat_add = 0
                if self.combo >= 4:
                    is_super_triggered = True
            else:
                self.combo = 0
                score_add = 10
                heat_add = 15
            self._last_color = dot.color
        return score_add, heat_add, is_super_triggered

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.phase = Phase.SUPER

    def _update_super(self) -> None:
        head = self.segments[0]
        for dot in self.dots:
            if not dot.alive:
                continue
            dist = math.hypot(head.x - dot.x, head.y - dot.y)
            if dist < SUPER_COLLECT_RADIUS:
                dot.alive = False
                score_add, _, _ = self._eat_dot(dot)
                self.score += score_add
                self._spawn_particles(dot.x, dot.y, 16, self._rng.choice(DOT_COLORS))
                self._spawn_floating_text(dot.x, dot.y - 6, f"+{score_add}", LIME)

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - 1.0)
        if self.heat >= 100.0 and self.phase not in (Phase.TITLE, Phase.GAME_OVER):
            self.phase = Phase.GAME_OVER
            if self.score > self._best_score:
                self._best_score = self.score
                self.best_ghost = self.ghost_points.copy()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-3.0, -1.0)
            life = self._rng.randint(10, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _record_ghost_point(self) -> None:
        head = self.segments[0]
        self.ghost_points.append(GhostPoint(x=head.x, y=head.y))

    # ---- Pyxel Callbacks ----

    def update(self) -> None:
        self.frame += 1
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.SUPER:
            self._update_playing()
            if self.phase == Phase.SUPER:
                self._update_super_state()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.SUPER):
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ---- Phase Handlers ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _update_playing(self) -> None:
        space_held = pyxel.btn(pyxel.KEY_SPACE)
        if space_held:
            self._contract_amount = min(1.0, self._contract_amount + 0.1)
        else:
            if self._prev_space:
                self._lunge_frames = LUNGE_DURATION
            self._contract_amount = max(0.0, self._contract_amount - 0.05)
        self._prev_space = space_held

        if self._lunge_frames > 0:
            self._lunge_frames -= 1

        self._update_worm()
        self._update_dots()

        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self.dots.append(self._spawn_dot())
            progress = min(1.0, self.frame / 3600.0)
            base = 55 - int(25 * progress)
            self._spawn_timer = self._rng.randint(
                max(25, base - 5), max(32, base + 5)
            )

        head = self.segments[0]
        for dot in self.dots:
            if not dot.alive:
                continue
            dist = math.hypot(head.x - dot.x, head.y - dot.y)
            if dist < EAT_RADIUS:
                dot.alive = False
                score_add, heat_add, is_super = self._eat_dot(dot)
                self.score += score_add
                self.heat += heat_add
                actual_color = DOT_COLORS[dot.color]
                self._spawn_particles(dot.x, dot.y, 8, actual_color)
                if is_super:
                    self._activate_super()
                    self._spawn_floating_text(head.x, head.y - 12, "SUPER INCH!", CYAN)
                    break
                elif self.combo > 1:
                    self._spawn_floating_text(head.x, head.y - 8, f"COMBO x{self.combo}", LIME)

        self._update_particles()
        self._update_floating_texts()
        self._update_heat()
        self._record_ghost_point()

    def _update_super_state(self) -> None:
        self.super_timer -= 1
        self._update_super()
        if self.super_timer <= 0:
            self.super_timer = 0
            self.phase = Phase.PLAYING
            self._last_color = -1

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.segments = [Segment(x=160.0 - i * 8.0, y=WORM_Y) for i in range(NUM_SEGMENTS)]
        self.dots = []
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.particles = []
        self.floating_texts = []
        self.ghost_points = []
        self.ground_scroll = 0.0
        self.frame = 0
        self._last_color = -1
        self._contract_amount = 0.0
        self._lunge_frames = 0
        self._spawn_timer = 20
        self._wave_phase = 0.0
        self._prev_space = False

    # ---- Drawing Methods ----

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 50, "INCH CHAIN", WHITE)

        demo_y = 80
        t = pyxel.frame_count * 0.1
        for i in range(NUM_SEGMENTS):
            dx = math.sin(t + i * 1.2) * 3
            pyxel.circ(130 + i * 10, demo_y + int(dx), 4, GREEN)
        pyxel.circ(130, demo_y, 5, GREEN)

        pyxel.text(SCREEN_W // 2 - 75, 108, "SPACE to start", LIME)
        pyxel.text(SCREEN_W // 2 - 75, 124, "Hold SPACE: Contract & Slow", GRAY)
        pyxel.text(SCREEN_W // 2 - 75, 138, "Release SPACE: Lunge Forward!", GRAY)
        pyxel.text(SCREEN_W // 2 - 75, 158, "Eat same-color dots -> COMBO!", ORANGE)
        pyxel.text(SCREEN_W // 2 - 75, 172, "COMBO x4 -> SUPER INCH! (3x score)", CYAN)
        pyxel.text(SCREEN_W // 2 - 75, 190, "Wrong color -> +HEAT, reset combo", RED)

        if self._best_score > 0:
            best_text = f"Best: {self._best_score}  (ghost replay ON)"
            pyxel.text(SCREEN_W // 2 - 70, 220, best_text, YELLOW)

    def _draw_playing(self) -> None:
        self._draw_ground()
        self._draw_ghost()
        self._draw_dots()
        self._draw_worm()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_ground(self) -> None:
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, BROWN)
        offset = int(self.ground_scroll) % 40
        for x in range(-offset, SCREEN_W + 40, 40):
            pyxel.pset(x, GROUND_Y - 2, DARK_BLUE)
            pyxel.pset(x + 10, GROUND_Y - 1, GREEN)
            pyxel.pset(x + 20, GROUND_Y - 3, DARK_BLUE)
            pyxel.pset(x + 30, GROUND_Y - 2, GREEN)

    def _draw_ghost(self) -> None:
        if not self.best_ghost:
            return
        for gp in self.best_ghost:
            if int(gp.x + gp.y) % 3 == 0:
                pyxel.pset(int(gp.x), int(gp.y), GRAY)

    def _draw_dots(self) -> None:
        for dot in self.dots:
            if dot.alive:
                color = DOT_COLORS[dot.color]
                pyxel.circ(int(dot.x), int(dot.y), 3, color)
                pyxel.pset(int(dot.x), int(dot.y), WHITE)

    def _draw_worm(self) -> None:
        for i in range(len(self.segments) - 1, 0, -1):
            seg = self.segments[i]
            prev = self.segments[i - 1]
            if self.super_timer > 0:
                color = DOT_COLORS[(self.frame // 8 + i) % 4]
            else:
                color = GREEN
            pyxel.line(int(prev.x), int(prev.y), int(seg.x), int(seg.y), color)
            pyxel.circ(int(seg.x), int(seg.y), 4, color)

        head = self.segments[0]
        if self.super_timer > 0:
            head_color = DOT_COLORS[(self.frame // 8) % 4]
        else:
            head_color = GREEN
        pyxel.circ(int(head.x), int(head.y), 5, head_color)
        pyxel.pset(int(head.x) + 2, int(head.y) - 1, WHITE)
        pyxel.pset(int(head.x) + 2, int(head.y) + 1, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20.0
            if alpha > 0.5:
                pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
            elif alpha > 0.2:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                tx = int(ft.x) - len(ft.text) * 2
                pyxel.text(tx, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        if self.combo > 0:
            c = CYAN if self.combo >= 4 else LIME
            pyxel.text(4, 14, f"COMBO x{self.combo}", c)
        pyxel.text(SCREEN_W - 72, 4, f"MAX:{self.max_combo}", GRAY)

        bx, by, bw, bh = 4, 26, 64, 4
        hr = min(1.0, self.heat / 100.0)
        hc = RED if self.heat > 70 else ORANGE
        pyxel.rect(bx, by, bw, bh, GRAY)
        pyxel.rect(bx, by, int(bw * hr), bh, hc)
        pyxel.text(bx + bw + 4, by - 1, "HEAT", hc)

        if self.super_timer > 0:
            tx, ty, tw, th = 4, 33, 80, 4
            tr = self.super_timer / SUPER_DURATION
            pyxel.rect(tx, ty, tw, th, GRAY)
            pyxel.rect(tx, ty, int(tw * tr), th, CYAN)
            pyxel.text(tx + tw + 4, ty - 1, "SUPER", CYAN)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 65, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 44, 95, f"Final Score: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 44, 112, f"Max Combo:   {self.max_combo}", LIME)

        if self._best_score > 0:
            best_text = f"Best Score:  {self._best_score}"
            pyxel.text(SCREEN_W // 2 - 44, 132, best_text, YELLOW)

        if self.heat >= 100.0:
            pyxel.text(SCREEN_W // 2 - 60, 155, "Overheated! Avoid wrong colors.", ORANGE)

        if self.super_timer > 0:
            pyxel.text(SCREEN_W // 2 - 40, 175, "SUPER INCH was active!", CYAN)

        pyxel.text(SCREEN_W // 2 - 48, 200, "SPACE to retry", WHITE)


if __name__ == "__main__":
    Game()
