"""DEPTH CHAIN - Free-diving pearl collection game. Chain same-color pearls for SUPER BREATH."""
import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ---- Constants ----
SCREEN_W = 320
SCREEN_H = 240
DIVER_W = 12
DIVER_H = 16
DIVER_X = SCREEN_W // 2 - DIVER_W // 2
MAX_OXYGEN = 100.0
OXYGEN_DECAY = 0.03
OXYGEN_ASCENT_COST = 0.08
MAX_HEAT = 100.0
HEAT_DECAY = 0.02
HEAT_WRONG = 15.0
COMBO_THRESHOLD = 4
SUPER_DURATION = 300
PEARL_COUNT = 12
PEARL_SPAWN_INTERVAL = 60
DARKNESS_RISE_SPEED = 0.02
SCROLL_SPEED = 0.3
SWIM_SPEED = 2.0
MOVE_SPEED = 1.5
SUPER_COLLECT_RADIUS = 40
GLOW_RADIUS = 5
DIVER_RADIUS = 9
PEARL_RADIUS = 4
COLLISION_DIST = DIVER_RADIUS + PEARL_RADIUS

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

COLOR_VALS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---- Data Classes ----

@dataclass
class Pearl:
    x: float
    y: float
    color: int
    collected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ---- Game Class ----

class Game:
    # Class-level constants for testability
    MAX_OXYGEN: ClassVar[float] = MAX_OXYGEN
    OXYGEN_DECAY: ClassVar[float] = OXYGEN_DECAY
    OXYGEN_ASCENT_COST: ClassVar[float] = OXYGEN_ASCENT_COST
    MAX_HEAT: ClassVar[float] = MAX_HEAT
    HEAT_DECAY: ClassVar[float] = HEAT_DECAY
    HEAT_WRONG: ClassVar[float] = HEAT_WRONG
    COMBO_THRESHOLD: ClassVar[int] = COMBO_THRESHOLD
    SUPER_DURATION: ClassVar[int] = SUPER_DURATION
    PEARL_COUNT: ClassVar[int] = PEARL_COUNT
    PEARL_SPAWN_INTERVAL: ClassVar[int] = PEARL_SPAWN_INTERVAL
    DARKNESS_RISE_SPEED: ClassVar[float] = DARKNESS_RISE_SPEED
    SCROLL_SPEED: ClassVar[float] = SCROLL_SPEED
    SWIM_SPEED: ClassVar[float] = SWIM_SPEED
    MOVE_SPEED: ClassVar[float] = MOVE_SPEED
    SUPER_COLLECT_RADIUS: ClassVar[int] = SUPER_COLLECT_RADIUS
    COLLISION_DIST: ClassVar[float] = COLLISION_DIST
    SCREEN_W: ClassVar[int] = SCREEN_W
    SCREEN_H: ClassVar[int] = SCREEN_H
    DIVER_W: ClassVar[int] = DIVER_W
    DIVER_H: ClassVar[int] = DIVER_H
    DIVER_X: ClassVar[int] = DIVER_X

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="DEPTH CHAIN", display_scale=2)
        self._rng: random.Random
        self.phase: Phase
        self.diver_x: float
        self.diver_y: float
        self.oxygen: float
        self.heat: float
        self.score: int
        self.combo: int
        self.max_combo: int
        self.current_color: int
        self.super_timer: int
        self.darkness_y: float
        self.pearls: list[Pearl]
        self.particles: list[Particle]
        self.floating_texts: list[FloatingText]
        self.frame: int
        self.spawn_timer: int
        self.depth: float
        self.total_pearls_collected: int
        self._best_score: int
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.TITLE
        self.diver_x = float(DIVER_X)
        self.diver_y = 60.0
        self.oxygen = MAX_OXYGEN
        self.heat = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.current_color = -1
        self.super_timer = 0
        self.darkness_y = float(SCREEN_H - 40)
        self.pearls = []
        self.particles = []
        self.floating_texts = []
        self.frame = 0
        self.spawn_timer = 0
        self.depth = 0.0
        self.total_pearls_collected = 0
        self._best_score = 0

    # ---- Depth Multiplier ----

    @staticmethod
    def calc_depth_mult(depth: float) -> float:
        return min(10.0, 1.0 + depth / 500.0)

    # ---- Pearl Spawning ----

    def _spawn_pearl(self) -> Pearl:
        color = self._rng.randint(0, 3)
        x = self._rng.uniform(20, float(SCREEN_W - 20))
        y = self._rng.uniform(-10, 0)
        return Pearl(x=x, y=y, color=color)

    def _update_spawn(self) -> None:
        if len(self.pearls) < PEARL_COUNT:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.pearls.append(self._spawn_pearl())
                self.spawn_timer = PEARL_SPAWN_INTERVAL

    # ---- Pearl Updates ----

    def _update_pearls(self) -> None:
        for pearl in self.pearls:
            pearl.y += SCROLL_SPEED
        self.pearls = [p for p in self.pearls if p.y < SCREEN_H + 10 and not p.collected]

    # ---- Collection Check ----

    def _check_collection(self) -> None:
        diver_cx = self.diver_x + DIVER_W / 2
        diver_cy = self.diver_y + DIVER_H / 2
        for pearl in self.pearls:
            if pearl.collected:
                continue
            pcx = pearl.x
            pcy = pearl.y
            dist = math.hypot(diver_cx - pcx, diver_cy - pcy)

            if self.super_timer > 0:
                if dist < SUPER_COLLECT_RADIUS:
                    self._collect_pearl(pearl, same_color=True)
            else:
                if dist < COLLISION_DIST:
                    same = (pearl.color == self.current_color)
                    self._collect_pearl(pearl, same_color=same)

    def _collect_pearl(self, pearl: Pearl, *, same_color: bool) -> None:
        pearl.collected = True
        self.total_pearls_collected += 1
        depth_mult = self.calc_depth_mult(self.depth)
        actual_color = COLOR_VALS[pearl.color]

        if self.super_timer > 0:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            score_add = int((10 + self.combo * 5) * depth_mult * 3.0)
            self.score += score_add
            self.oxygen = min(MAX_OXYGEN, self.oxygen + 0.5)
            self._spawn_particles(pearl.x, pearl.y, 12, actual_color)
            self._spawn_floating_text(pearl.x, pearl.y - 6, f"+{score_add}", LIME)
        elif same_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            score_add = int((10 + self.combo * 5) * depth_mult)
            self.score += score_add
            self._spawn_particles(pearl.x, pearl.y, 8, actual_color)
            if self.combo > 1:
                self._spawn_floating_text(pearl.x, pearl.y - 6, f"COMBO x{self.combo}", LIME)
            if self.combo >= COMBO_THRESHOLD and self.super_timer <= 0:
                self._activate_super()
        else:
            self.heat = min(MAX_HEAT, self.heat + HEAT_WRONG)
            self.combo = 0
            self.current_color = pearl.color
            score_add = int(10 * depth_mult)
            self.score += score_add
            self._spawn_particles(pearl.x, pearl.y, 4, RED)
            self._spawn_floating_text(pearl.x, pearl.y - 6, "WRONG!", ORANGE)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(
            float(SCREEN_W // 2 - 28), float(SCREEN_H // 2),
            "SUPER BREATH!", CYAN,
        )
        for _ in range(30):
            px = self._rng.uniform(0, float(SCREEN_W))
            py = self._rng.uniform(0, float(SCREEN_H))
            color = COLOR_VALS[self._rng.randint(0, 3)]
            vx = self._rng.uniform(-3, 3)
            vy = self._rng.uniform(-3, 3)
            life = self._rng.randint(20, 40)
            self.particles.append(Particle(x=px, y=py, vx=vx, vy=vy, life=life, color=color))

    # ---- Super Mode ----

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_timer = 0

    # ---- Oxygen, Heat, Darkness ----

    def _update_oxygen(self, space_held: bool) -> bool:
        if self.oxygen <= 0:
            return True
        decay = OXYGEN_DECAY
        if space_held:
            decay += OXYGEN_ASCENT_COST
        if self.diver_y > self.darkness_y:
            decay *= 4.0
        self.oxygen -= decay
        return False

    def _update_heat(self) -> bool:
        if self.heat >= MAX_HEAT:
            return True
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        return False

    def _update_darkness(self) -> None:
        self.darkness_y -= DARKNESS_RISE_SPEED

    # ---- Particle & Floating Text Systems ----

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            life = self._rng.randint(10, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

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

    # ---- Ambient Bubbles ----

    def _spawn_ambient_bubbles(self) -> None:
        if self._rng.random() < 0.15:
            bx = self._rng.uniform(0, float(SCREEN_W))
            by = float(SCREEN_H + 4)
            bvy = self._rng.uniform(-1.0, -0.3)
            life = self._rng.randint(30, 90)
            self.particles.append(
                Particle(x=bx, y=by, vx=0.0, vy=bvy, life=life, color=LIGHT_BLUE, size=1)
            )

    # ---- Pyxel Callbacks ----

    def update(self) -> None:
        self.frame += 1
        self._spawn_ambient_bubbles()
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ---- Phase: TITLE ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._start_game()

    def _draw_title(self) -> None:
        self._draw_ocean_background()
        t = pyxel.frame_count * 0.05
        depth_y = int(SCREEN_H * 0.15 + math.sin(t) * 4)
        pyxel.text(SCREEN_W // 2 - 42, depth_y, "DEPTH CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, depth_y + 14, "Free Dive. Chain Pearls. Survive.", GRAY)

        y = int(depth_y + 45)
        pyxel.text(SCREEN_W // 2 - 55, y, "LEFT/RIGHT : Move horizontally", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 55, y + 12, "SPACE      : Swim upward", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 55, y + 26, "Same color  -> COMBO!", LIME)
        pyxel.text(SCREEN_W // 2 - 55, y + 38, "COMBO x4    -> SUPER BREATH", CYAN)
        pyxel.text(SCREEN_W // 2 - 55, y + 50, "Wrong color -> +HEAT, reset", ORANGE)

        pyxel.text(SCREEN_W // 2 - 55, y + 72, "PRESS SPACE TO START", WHITE)

        if self._best_score > 0:
            best_text = f"Best Score: {self._best_score}"
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H - 16, best_text, YELLOW)

    # ---- Phase: PLAYING ----

    def _update_playing(self) -> None:
        space_held = pyxel.btn(pyxel.KEY_SPACE)

        # Input: horizontal movement
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.diver_x -= MOVE_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.diver_x += MOVE_SPEED
        self.diver_x = max(20.0, min(float(SCREEN_W - 20 - DIVER_W), self.diver_x))

        # Input: vertical movement
        if space_held:
            self.diver_y -= SWIM_SPEED
            self.diver_y = max(10.0, self.diver_y)
        else:
            self.diver_y += SCROLL_SPEED

        # Depth tracking
        self.depth += SCROLL_SPEED
        if space_held:
            self.depth -= SWIM_SPEED
        self.depth = max(0.0, self.depth)

        # Oxygen
        if self._update_oxygen(space_held):
            self._end_game()

        # Heat
        if self._update_heat():
            self._end_game()

        # Darkness
        self._update_darkness()

        # Super timer
        self._update_super()

        # Spawn & update pearls
        self._update_spawn()
        self._update_pearls()

        # Check collisions
        self._check_collection()

        # Particle & floating text systems
        self._update_particles()
        self._update_floating_texts()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.diver_x = float(DIVER_X)
        self.diver_y = 60.0
        self.oxygen = MAX_OXYGEN
        self.heat = 0.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.current_color = -1
        self.super_timer = 0
        self.darkness_y = float(SCREEN_H - 40)
        self.pearls = []
        self.particles = []
        self.floating_texts = []
        self.frame = 0
        self.spawn_timer = 30
        self.depth = 0.0
        self.total_pearls_collected = 0

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self._best_score:
            self._best_score = self.score

    # ---- Phase: GAME_OVER ----

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._start_game()

    def _draw_game_over(self) -> None:
        self._draw_ocean_background()
        pyxel.text(SCREEN_W // 2 - 32, 50, "GAME OVER", RED)

        pyxel.text(SCREEN_W // 2 - 55, 80, f"Final Score: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 94, f"Max Combo:   {self.max_combo}", LIME)
        pyxel.text(SCREEN_W // 2 - 55, 108, f"Depth:       {self.depth:.0f}m", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 55, 122, f"Pearls:      {self.total_pearls_collected}", WHITE)

        if self.heat >= MAX_HEAT:
            pyxel.text(SCREEN_W // 2 - 65, 150, "OVERHEATED! Avoid wrong colors.", ORANGE)
        if self.oxygen <= 0:
            pyxel.text(SCREEN_W // 2 - 65, 162, "DROWNED! Oxygen ran out.", CYAN)

        if self._best_score > 0 and self._best_score == self.score:
            pyxel.text(SCREEN_W // 2 - 40, 185, "NEW BEST SCORE!", YELLOW)

        pyxel.text(SCREEN_W // 2 - 48, 210, "PRESS SPACE TO RETRY", WHITE)

    # ---- Drawing: PLAYING ----

    def _draw_playing(self) -> None:
        self._draw_ocean_background()
        self._draw_darkness()
        self._draw_pearls()
        self._draw_diver()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    # ---- Ocean Background ----

    def _draw_ocean_background(self) -> None:
        bands = [
            (0, NAVY),
            (60, DARK_BLUE),
            (120, PURPLE),
            (180, NAVY),
        ]
        for y, color in bands:
            pyxel.rect(0, y, SCREEN_W, 60, color)

    # ---- Darkness Overlay ----

    def _draw_darkness(self) -> None:
        dy = int(self.darkness_y)
        if dy < SCREEN_H:
            h = SCREEN_H - dy
            for i in range(h):
                shade = int(5 - (i / max(1, h)) * 5)
                shade = max(0, shade)
                if shade == 0:
                    shade = 0
                pyxel.line(0, dy + i, SCREEN_W, dy + i, shade)

    # ---- Pearls ----

    def _draw_pearls(self) -> None:
        for pearl in self.pearls:
            if pearl.collected:
                continue
            color = COLOR_VALS[pearl.color]
            ix, iy = int(pearl.x), int(pearl.y)
            pyxel.circ(ix, iy, GLOW_RADIUS, BLACK)
            pyxel.circ(ix, iy, PEARL_RADIUS, color)
            pyxel.pset(ix + 1, iy - 1, WHITE)

    # ---- Diver ----

    def _draw_diver(self) -> None:
        dx = int(self.diver_x)
        dy = int(self.diver_y)

        if self.super_timer > 0:
            diver_color = COLOR_VALS[(self.frame // 6) % 4]
        elif self.current_color >= 0:
            diver_color = COLOR_VALS[self.current_color]
        else:
            diver_color = WHITE

        # Body
        pyxel.rect(dx + 2, dy + 6, 8, 10, diver_color)
        # Head
        pyxel.circ(dx + 6, dy + 6, 4, diver_color)
        # Eye
        if diver_color == YELLOW:
            eye_color = BLACK
        else:
            eye_color = WHITE
        pyxel.pset(dx + 8, dy + 5, eye_color)

    # ---- Particles ----

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.5:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)
            elif alpha > 0.2:
                pyxel.pset(int(p.x), int(p.y), p.color)

    # ---- Floating Texts ----

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                tx = int(ft.x) - len(ft.text) * 2
                pyxel.text(tx, int(ft.y), ft.text, ft.color)

    # ---- HUD ----

    def _draw_hud(self) -> None:
        # Oxygen bar (top-left)
        ox_pct = max(0.0, self.oxygen / MAX_OXYGEN)
        ox_color = GREEN if ox_pct > 0.5 else (YELLOW if ox_pct > 0.25 else RED)
        pyxel.rect(4, 4, 64, 6, GRAY)
        pyxel.rect(4, 4, int(64 * ox_pct), 6, ox_color)
        pyxel.text(72, 3, "O2", WHITE)

        # Score (top-center)
        score_text = f"{self.score:06d}"
        pyxel.text(SCREEN_W // 2 - 18, 4, score_text, WHITE)

        # Depth (top-right area)
        depth_text = f"{self.depth:.0f}m"
        pyxel.text(SCREEN_W - 50, 4, depth_text, LIGHT_BLUE)

        # Combo display (large center-top)
        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            if self.combo >= COMBO_THRESHOLD:
                c = CYAN
            else:
                c = LIME
            pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 16, combo_text, c)

        # Super timer bar
        if self.super_timer > 0:
            tx, ty, tw, th = 4, 14, 80, 4
            tr = self.super_timer / SUPER_DURATION
            pyxel.rect(tx, ty, tw, th, GRAY)
            pyxel.rect(tx, ty, int(tw * tr), th, CYAN)
            pyxel.text(tx + tw + 4, ty - 1, "SUPER", CYAN)

        # Heat bar (bottom)
        heat_pct = self.heat / MAX_HEAT
        heat_color = RED if heat_pct > 0.7 else ORANGE
        pyxel.rect(4, SCREEN_H - 14, 64, 6, GRAY)
        pyxel.rect(4, SCREEN_H - 14, int(64 * heat_pct), 6, heat_color)
        pyxel.text(72, SCREEN_H - 15, "HEAT", heat_color)

        # Max combo small
        pyxel.text(SCREEN_W - 60, SCREEN_H - 15, f"MAX:{self.max_combo}", GRAY)


if __name__ == "__main__":
    Game()
