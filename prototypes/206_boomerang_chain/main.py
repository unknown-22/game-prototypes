"""
Boomerang Chain - 206
A boomerang-throwing arcade game: chain hits on same-colored targets.
Chain 4+ same-color hits in one throw to activate SUPER MODE!
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
PLAYER_X = 160
PLAYER_Y = 220
PLAYER_RADIUS = 10
CATCH_RADIUS = 16
CATCH_RADIUS_MIN_DRAG = 20
BOOMERANG_RADIUS = 4
BOOMERANG_TRAIL_MAX = 15
BOOMERANG_CURVE_RATE = 0.035
BOOMERANG_SPEED_MIN = 2.0
BOOMERANG_SPEED_MAX = 4.0
BOOMERANG_SPEED_RANGE = BOOMERANG_SPEED_MAX - BOOMERANG_SPEED_MIN
POWER_MAX_DRAG = 100.0
TARGET_SIZE = 14
TARGET_HALF = TARGET_SIZE // 2
TARGET_COUNT = 12
TARGETS_PER_COLOR = 3
TARGET_SPAWN_X_MIN = 20
TARGET_SPAWN_X_MAX = 300
TARGET_SPAWN_Y_MIN = 20
TARGET_SPAWN_Y_MAX = 185
TARGET_MIN_SEP = TARGET_SIZE + 4
RESOLVE_DURATION = 30
HEAT_MAX = 100.0
HEAT_PER_WRONG = 10.0
HEAT_DECAY = 0.5
GAME_DURATION = 3600
SUPER_DURATION = 180
SUPER_REQUIRED_COMBO = 4
MIN_FLY_FRAMES = 20
SCREEN_SHAKE_FRAMES = 3

# Colors (raw ints)
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

TARGET_COLORS = [RED, GREEN, LIGHT_BLUE, YELLOW]
COLOR_CYCLE = TARGET_COLORS
RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE, PINK]
COLOR_BORDERS = {RED: NAVY, GREEN: NAVY, LIGHT_BLUE: DARK_BLUE, YELLOW: BROWN}


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    RESOLVE = auto()
    GAME_OVER = auto()


@dataclass
class Target:
    x: float
    y: float
    color: int
    alive: bool = True


@dataclass
class Boomerang:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    alive: bool = True
    trail: list[tuple[float, float]] = field(default_factory=list)
    max_trail: int = BOOMERANG_TRAIL_MAX
    fly_frames: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.05


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    """Boomerang Chain -- main game class."""

    def __init__(self) -> None:
        self._rng_seed: int | None = None

    def reset(self) -> None:
        seed = getattr(self, "_rng_seed", None) or random.randint(0, 2**31 - 1)
        self._rng = random.Random(seed)
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: int = GAME_DURATION
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.aim_active: bool = False
        self.aim_end_x: float = 0.0
        self.aim_end_y: float = 0.0
        self.boomerang: Boomerang | None = None
        self.boomerang_color_idx: int = 0
        self.boomerang_color: int = COLOR_CYCLE[0]
        self.targets: list[Target] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.best_score: int = 0
        self.shake_frames: int = 0
        self.resolve_timer: int = 0
        self.frame: int = 0
        self.hit_targets_this_throw: set[int] = set()
        self._spawn_targets()

    # --- Target Spawning ---

    def _spawn_targets(self) -> None:
        self.targets.clear()
        for color in TARGET_COLORS:
            for _ in range(TARGETS_PER_COLOR):
                self._spawn_single_target(color)

    def _spawn_single_target(self, color: int) -> None:
        for _ in range(200):
            x = self._rng.uniform(TARGET_SPAWN_X_MIN, TARGET_SPAWN_X_MAX)
            y = self._rng.uniform(TARGET_SPAWN_Y_MIN, TARGET_SPAWN_Y_MAX)
            too_close = any(
                abs(t.x - x) < TARGET_MIN_SEP and abs(t.y - y) < TARGET_MIN_SEP
                for t in self.targets
                if t.alive
            )
            if not too_close:
                self.targets.append(Target(x=x, y=y, color=color))
                return
        self.targets.append(Target(x=x, y=y, color=color))

    def _respawn_targets(self) -> None:
        alive_count = sum(1 for t in self.targets if t.alive)
        if alive_count >= TARGET_COUNT:
            return
        for target in self.targets:
            if target.alive:
                continue
            color = self._rng.choice(TARGET_COLORS)
            for _ in range(200):
                x = self._rng.uniform(TARGET_SPAWN_X_MIN, TARGET_SPAWN_X_MAX)
                y = self._rng.uniform(TARGET_SPAWN_Y_MIN, TARGET_SPAWN_Y_MAX)
                too_close = any(
                    abs(t.x - x) < TARGET_MIN_SEP and abs(t.y - y) < TARGET_MIN_SEP
                    for t in self.targets
                    if t.alive and t is not target
                )
                if not too_close:
                    target.x = x
                    target.y = y
                    target.color = color
                    target.alive = True
                    break
            else:
                target.x = x
                target.y = y
                target.color = color
                target.alive = True

    # --- Boomerang ---

    def _launch_boomerang(self, angle: float, speed: float) -> None:
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        color = self.boomerang_color
        self.boomerang = Boomerang(
            x=PLAYER_X,
            y=PLAYER_Y,
            vx=vx,
            vy=vy,
            color=color,
        )
        self.hit_targets_this_throw.clear()

    def _update_boomerang(self) -> None:
        if self.boomerang is None or not self.boomerang.alive:
            return
        b = self.boomerang
        b.trail.append((b.x, b.y))
        if len(b.trail) > b.max_trail:
            b.trail.pop(0)
        ovx, ovy = b.vx, b.vy
        ca = math.cos(BOOMERANG_CURVE_RATE)
        sa = math.sin(BOOMERANG_CURVE_RATE)
        b.vx = ovx * ca - ovy * sa
        b.vy = ovx * sa + ovy * ca
        b.x += b.vx
        b.y += b.vy
        b.x = max(0.0, min(SCREEN_W, b.x))
        b.y = max(0.0, min(SCREEN_H, b.y))
        b.fly_frames += 1

    def _check_target_collisions(self) -> list[Target]:
        if self.boomerang is None or not self.boomerang.alive:
            return []
        hits: list[Target] = []
        bx, by = self.boomerang.x, self.boomerang.y
        for i, target in enumerate(self.targets):
            if not target.alive:
                continue
            if i in self.hit_targets_this_throw:
                continue
            if abs(bx - target.x) < TARGET_HALF + BOOMERANG_RADIUS and abs(
                by - target.y
            ) < TARGET_HALF + BOOMERANG_RADIUS:
                hits.append(target)
                self.hit_targets_this_throw.add(i)
        return hits

    def _handle_hit(self, target: Target) -> None:
        target.alive = False
        b = self.boomerang
        if b is None:
            return
        if self.super_mode:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            base = int(100 * (1 + self.combo * 0.5))
            total = base * 3
            self.score += total
            self._spawn_hit_particles(
                target.x, target.y, b.color, 20, 1.0, 3.5, 25, 35
            )
            self._spawn_floating_text(target.x, target.y, f"+{total}", YELLOW)
            if self.combo >= 2:
                self._spawn_floating_text(
                    target.x, target.y - 10, f"x{self.combo}", WHITE
                )
        elif b.color == target.color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            base = int(100 * (1 + self.combo * 0.5))
            self.score += base
            self._spawn_hit_particles(
                target.x, target.y, target.color, 12, 1.0, 3.0, 20, 30
            )
            self._spawn_floating_text(target.x, target.y, f"+{base}", target.color)
            if self.combo >= 2:
                self._spawn_floating_text(
                    target.x, target.y - 10, f"x{self.combo}", WHITE
                )
        else:
            self.combo = 0
            self.score += 100
            self.heat = min(HEAT_MAX, self.heat + HEAT_PER_WRONG)
            self._spawn_hit_particles(
                target.x, target.y, GRAY, 6, 0.5, 1.5, 10, 15
            )
            self._spawn_floating_text(target.x, target.y, "+100", GRAY)

    def _handle_catch(self) -> None:
        if self.boomerang is not None:
            self._spawn_catch_particles()
        if self.super_mode:
            self.super_mode = False
            self.super_timer = 0
        if self.combo >= SUPER_REQUIRED_COMBO:
            self._activate_super()
        self.boomerang = None
        self.boomerang_color_idx = (self.boomerang_color_idx + 1) % len(COLOR_CYCLE)
        self.boomerang_color = COLOR_CYCLE[self.boomerang_color_idx]
        if self.score > self.best_score:
            self.best_score = self.score
        if self.game_timer <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
        else:
            self.phase = Phase.RESOLVE
            self.resolve_timer = RESOLVE_DURATION

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.shake_frames = SCREEN_SHAKE_FRAMES
        self._spawn_floating_text(PLAYER_X, PLAYER_Y - 30, "SUPER!", YELLOW)
        for _ in range(30):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 4.0)
            color = self._rng.choice(TARGET_COLORS)
            life = self._rng.randint(20, 40)
            self.particles.append(
                Particle(
                    x=PLAYER_X,
                    y=PLAYER_Y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    color=color,
                )
            )

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # --- Particles & Text ---

    def _spawn_hit_particles(
        self,
        x: float,
        y: float,
        color: int,
        count: int,
        min_speed: float,
        max_speed: float,
        min_life: int,
        max_life: int,
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(min_speed, max_speed)
            life = self._rng.randint(min_life, max_life)
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

    def _spawn_catch_particles(self) -> None:
        for _ in range(8):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 2.0)
            life = self._rng.randint(10, 20)
            self.particles.append(
                Particle(
                    x=PLAYER_X,
                    y=PLAYER_Y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    color=WHITE,
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(
                x=x,
                y=y,
                text=text,
                life=Game.FLOAT_LIFE,
                color=color,
            )
        )

    FLOAT_LIFE = 30

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.vy += p.gravity
            p.vx *= 0.98
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # --- Helpers ---

    def _super_color(self) -> int:
        return RAINBOW_COLORS[(self.frame // 4) % len(RAINBOW_COLORS)]

    def _go_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # --- Update ---

    def update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.AIMING

        elif self.phase == Phase.AIMING:
            self.game_timer = max(0, self.game_timer - 1)
            self._update_heat()
            self._update_particles()
            self._update_floating_texts()
            if self.game_timer <= 0 or self.heat >= HEAT_MAX:
                self._go_game_over()
                return
            if not self.aim_active and pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                dx = pyxel.mouse_x - PLAYER_X
                dy = pyxel.mouse_y - PLAYER_Y
                if math.hypot(dx, dy) < CATCH_RADIUS_MIN_DRAG:
                    self.aim_active = True
                    self.aim_end_x = pyxel.mouse_x
                    self.aim_end_y = pyxel.mouse_y
            if self.aim_active:
                self.aim_end_x = pyxel.mouse_x
                self.aim_end_y = pyxel.mouse_y
                if not pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                    dx = self.aim_end_x - PLAYER_X
                    dy = self.aim_end_y - PLAYER_Y
                    dist = math.hypot(dx, dy)
                    if dist > 5.0:
                        angle = math.atan2(dy, dx)
                        power = min(1.0, dist / POWER_MAX_DRAG)
                        speed = (
                            BOOMERANG_SPEED_MIN + power * BOOMERANG_SPEED_RANGE
                        )
                        self._launch_boomerang(angle, speed)
                        self.phase = Phase.FLYING
                    self.aim_active = False

        elif self.phase == Phase.FLYING:
            self.game_timer = max(0, self.game_timer - 1)
            self._update_heat()
            self._update_particles()
            self._update_floating_texts()
            if self.super_mode:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self.super_mode = False
            self._update_boomerang()
            if self.boomerang is not None and self.boomerang.alive:
                hits = self._check_target_collisions()
                for target in hits:
                    self._handle_hit(target)
                b = self.boomerang
                if b.fly_frames > MIN_FLY_FRAMES:
                    dx = b.x - PLAYER_X
                    dy = b.y - PLAYER_Y
                    if math.hypot(dx, dy) < CATCH_RADIUS:
                        self._handle_catch()
            else:
                self._handle_catch()

        elif self.phase == Phase.RESOLVE:
            self.game_timer = max(0, self.game_timer - 1)
            self._update_heat()
            self._update_particles()
            self._update_floating_texts()
            self.resolve_timer -= 1
            if self.resolve_timer <= 0:
                self._respawn_targets()
                self.phase = Phase.AIMING
                self.aim_active = False

        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.AIMING

        if self.shake_frames > 0:
            self.shake_frames -= 1

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_game()
        self._draw_hud()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 56, 70, "BOOMERANG CHAIN", RED)
        pyxel.text(SCREEN_W // 2 - 60, 90, "Click or ENTER to Start", WHITE)
        pyxel.text(SCREEN_W // 2 - 72, 120, "Drag from player to aim & throw", GRAY)
        pyxel.text(
            SCREEN_W // 2 - 80, 130, "Hit same-color targets to build COMBO", GRAY
        )
        pyxel.text(SCREEN_W // 2 - 64, 140, "x4 combo  ->  SUPER MODE!", YELLOW)
        pyxel.text(
            SCREEN_W // 2 - 60,
            160,
            "Wrong color adds HEAT (game over at 100)",
            GRAY,
        )
        pyxel.text(SCREEN_W // 2 - 52, 180, "Survive 60 seconds!", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 28, 70, "GAME OVER", RED)
        pyxel.text(
            SCREEN_W // 2 - 40, 100, f"Score: {self.score}", WHITE
        )
        pyxel.text(
            SCREEN_W // 2 - 44, 110, f"Best:   {self.best_score}", YELLOW
        )
        pyxel.text(
            SCREEN_W // 2 - 40, 120, f"Max Combo: x{self.max_combo}", GREEN
        )
        pyxel.text(
            SCREEN_W // 2 - 76, 150, "Click or ENTER to Retry", WHITE
        )

    def _draw_game(self) -> None:
        # Handle screen shake via camera offset
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0 and self.phase not in (Phase.TITLE, Phase.GAME_OVER):
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
            try:
                pyxel.camera(shake_x, shake_y)
            except BaseException:
                pass

        # Targets
        for target in self.targets:
            if not target.alive:
                continue
            x1 = int(target.x - TARGET_HALF)
            y1 = int(target.y - TARGET_HALF)
            pyxel.rect(x1, y1, TARGET_SIZE, TARGET_SIZE, target.color)
            border = COLOR_BORDERS.get(target.color, BLACK)
            pyxel.rectb(x1, y1, TARGET_SIZE, TARGET_SIZE, border)

        # Boomerang trail
        b = self.boomerang
        if b is not None and b.alive and len(b.trail) > 1:
            for i, (tx, ty) in enumerate(b.trail):
                alpha = (i + 1) / len(b.trail)
                r = max(1, int(BOOMERANG_RADIUS * alpha * 0.8))
                if self.super_mode:
                    col = RAINBOW_COLORS[i % len(RAINBOW_COLORS)]
                else:
                    col = b.color
                pyxel.circ(int(tx), int(ty), r, col)

        # Boomerang
        if b is not None and b.alive:
            if self.super_mode:
                col = self._super_color()
            else:
                col = b.color
            pyxel.circ(int(b.x), int(b.y), BOOMERANG_RADIUS, col)
            pyxel.circ(int(b.x), int(b.y), BOOMERANG_RADIUS + 1, WHITE)

        # Particles
        for p in self.particles:
            alpha_ratio = p.life / 30.0
            if alpha_ratio > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for ft in self.floating_texts:
            alpha_ratio = ft.life / Game.FLOAT_LIFE
            if alpha_ratio > 0.2:
                col = ft.color if alpha_ratio > 0.5 else GRAY
                pyxel.text(
                    int(ft.x - len(ft.text) * 2),
                    int(ft.y),
                    ft.text,
                    col,
                )

        # Player
        player_color = self.boomerang_color
        if self.super_mode:
            player_color = self._super_color()
        pyxel.circ(PLAYER_X, PLAYER_Y, PLAYER_RADIUS, player_color)
        pyxel.circ(PLAYER_X, PLAYER_Y, PLAYER_RADIUS - 2, BLACK)
        pyxel.circ(PLAYER_X, PLAYER_Y, 3, player_color)

        # Aim line
        if self.aim_active and self.phase == Phase.AIMING:
            mx, my = self.aim_end_x, self.aim_end_y
            dist = math.hypot(mx - PLAYER_X, my - PLAYER_Y)
            power = min(1.0, dist / POWER_MAX_DRAG)
            if power < 0.33:
                aim_col = GREEN
            elif power < 0.66:
                aim_col = YELLOW
            else:
                aim_col = RED
            segments = max(1, int(dist / 8))
            for i in range(segments):
                t1 = i / segments
                t2 = min((i + 0.5) / segments, 1.0)
                x1 = PLAYER_X + (mx - PLAYER_X) * t1
                y1 = PLAYER_Y + (my - PLAYER_Y) * t1
                x2 = PLAYER_X + (mx - PLAYER_X) * t2
                y2 = PLAYER_Y + (my - PLAYER_Y) * t2
                pyxel.line(int(x1), int(y1), int(x2), int(y2), aim_col)

        # Reset camera
        if shake_x != 0 or shake_y != 0:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 11, BLACK)
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        combo_str = f"x{self.combo}" if self.combo > 0 else "x0"
        combo_x = SCREEN_W // 2 - len(combo_str) * 2
        combo_col = YELLOW if self.combo >= SUPER_REQUIRED_COMBO else WHITE
        pyxel.text(combo_x, 2, combo_str, combo_col)

        time_str = f"TIME:{max(0, self.game_timer // 60)}"
        time_x = SCREEN_W - 4 - len(time_str) * 4
        time_col = RED if self.game_timer < 600 else WHITE
        pyxel.text(time_x, 2, time_str, time_col)

        heat_bar_x = 180
        heat_bar_w = 60
        pyxel.text(heat_bar_x - 28, 2, "HEAT", GRAY)
        pyxel.rectb(heat_bar_x, 2, heat_bar_w, 7, GRAY)
        heat_fill = int(heat_bar_w * self.heat / HEAT_MAX)
        heat_col = RED if self.heat > 70 else YELLOW if self.heat > 40 else GREEN
        pyxel.rect(heat_bar_x + 1, 3, max(0, heat_fill - 2), 5, heat_col)

        if self.super_mode:
            sc = self._super_color()
            pyxel.text(SCREEN_W // 2 - 18, 12, "SUPER!", sc)

    # --- Entry Point ---

    @classmethod
    def run(cls) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Boomerang Chain", display_scale=2, fps=FPS)
        game = cls()
        game.reset()
        pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    Game.run()
