"""CHROMA ROUTE - 艦船を色付き滑走路に誘導する航路描画ゲーム"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import StrEnum

import pyxel

# ---- Constants ----
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_DURATION = 90 * FPS
SURGE_DURATION = 90
COLLISION_DIST = 12
LANDING_DIST = 14
WAYPOINT_REACH_DIST = 6
SHIP_SPEED_BASE = 1.5
SHIP_SPEED_FAST = 2.0
MAX_SHIPS_BASE = 8
MAX_SHIPS_LATE = 10
SPAWN_INTERVAL_INITIAL = 90
SPAWN_INTERVAL_MIN = 30
SPAWN_INTERVAL_DECREMENT = 2
LANDINGS_PER_DECREMENT = 10
SHIP_RADIUS = 6
PARTICLE_LIFE = 20
FLOAT_TEXT_LIFE = 40
WAYPOINT_RECORD_INTERVAL = 3

SHIP_COLORS: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_LIGHT_BLUE,
    pyxel.COLOR_YELLOW,
]

RUNWAY_SIDES: list[str] = ["top", "bottom", "left", "right"]

RUNWAY_DIM: dict[int, int] = {
    pyxel.COLOR_RED: pyxel.COLOR_BROWN,
    pyxel.COLOR_GREEN: pyxel.COLOR_LIME,
    pyxel.COLOR_LIGHT_BLUE: pyxel.COLOR_DARK_BLUE,
    pyxel.COLOR_YELLOW: pyxel.COLOR_ORANGE,
}

RAINBOW: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_ORANGE,
    pyxel.COLOR_YELLOW,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_LIGHT_BLUE,
    pyxel.COLOR_DARK_BLUE,
    pyxel.COLOR_PURPLE,
]


class Phase(StrEnum):
    TITLE = "TITLE"
    PLAYING = "PLAYING"
    GAME_OVER = "GAME_OVER"


# ---- Data Classes ----
@dataclass
class Ship:
    x: float
    y: float
    color: int
    target_runway: int
    path: list[tuple[float, float]] = field(default_factory=list)
    path_index: int = 0
    speed: float = SHIP_SPEED_BASE
    alive: bool = True


@dataclass
class Runway:
    x: int
    y: int
    w: int
    h: int
    color: int
    side: str

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


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
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA ROUTE", fps=FPS)
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.ships: list[Ship] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.surge_timer: int = 0
        self.landings: int = 0
        self.timer: int = GAME_DURATION
        self._spawn_timer: int = 0
        self.mislands: int = 0
        self.collisions: int = 0
        self.rng: random.Random = random.Random()

        self.drawing: bool = False
        self.drawing_ship: Ship | None = None
        self.drawing_path: list[tuple[float, float]] = []
        self._drawing_frame_counter: int = 0

        self.runways: list[Runway] = self._make_runways()

    @staticmethod
    def _make_runways() -> list[Runway]:
        rw, rh = 60, 16
        return [
            Runway(
                x=SCREEN_W // 2 - rw // 2,
                y=0,
                w=rw,
                h=rh,
                color=pyxel.COLOR_RED,
                side="top",
            ),
            Runway(
                x=SCREEN_W // 2 - rw // 2,
                y=SCREEN_H - rh,
                w=rw,
                h=rh,
                color=pyxel.COLOR_GREEN,
                side="bottom",
            ),
            Runway(
                x=0,
                y=SCREEN_H // 2 - rw // 2,
                w=rh,
                h=rw,
                color=pyxel.COLOR_LIGHT_BLUE,
                side="left",
            ),
            Runway(
                x=SCREEN_W - rh,
                y=SCREEN_H // 2 - rw // 2,
                w=rh,
                h=rw,
                color=pyxel.COLOR_YELLOW,
                side="right",
            ),
        ]

    def reset(self) -> None:
        self._init_state()
        self.phase = Phase.PLAYING
        self.rng = random.Random()

    # ---- Spawning ----
    def _spawn_interval(self) -> int:
        decrements = self.landings // LANDINGS_PER_DECREMENT
        interval = SPAWN_INTERVAL_INITIAL - decrements * SPAWN_INTERVAL_DECREMENT
        return max(SPAWN_INTERVAL_MIN, interval)

    def _max_ships(self) -> int:
        if self.landings >= 50:
            return MAX_SHIPS_LATE
        return MAX_SHIPS_BASE

    def _ship_speed(self) -> float:
        if self.landings >= 30:
            return SHIP_SPEED_FAST
        return SHIP_SPEED_BASE

    def _spawn_ship(self) -> Ship | None:
        alive = [s for s in self.ships if s.alive]
        if len(alive) >= self._max_ships():
            return None

        color_idx = self.rng.randint(0, 3)
        color = SHIP_COLORS[color_idx]
        runway_idx = color_idx

        runway = self.runways[runway_idx]
        speed = self._ship_speed()
        margin = 20

        if runway.side == "top":
            x = self.rng.uniform(margin, SCREEN_W - margin)
            y = SCREEN_H - margin
        elif runway.side == "bottom":
            x = self.rng.uniform(margin, SCREEN_W - margin)
            y = margin
        elif runway.side == "left":
            x = SCREEN_W - margin
            y = self.rng.uniform(margin, SCREEN_H - margin)
        else:
            x = margin
            y = self.rng.uniform(margin, SCREEN_H - margin)

        ship = Ship(
            x=x,
            y=y,
            color=color,
            target_runway=runway_idx,
            speed=speed,
        )
        self.ships.append(ship)
        return ship

    def _try_spawn(self) -> None:
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_ship()
            self._spawn_timer = self._spawn_interval()

    # ---- Ship Movement ----
    @staticmethod
    def _update_ship(ship: Ship, runway: Runway) -> None:
        if not ship.alive:
            return

        if ship.path_index < len(ship.path):
            tx, ty = ship.path[ship.path_index]
            dx = tx - ship.x
            dy = ty - ship.y
            dist = math.hypot(dx, dy)
            if dist < WAYPOINT_REACH_DIST:
                ship.path_index += 1
            elif dist > 0:
                ship.x += dx / dist * ship.speed
                ship.y += dy / dist * ship.speed
        else:
            tx = runway.cx
            ty = runway.cy
            dx = tx - ship.x
            dy = ty - ship.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                ship.x += dx / dist * ship.speed
                ship.y += dy / dist * ship.speed

    # ---- Path Drawing ----
    def _find_ship_at(self, mx: int, my: int) -> Ship | None:
        if self.drawing and self.drawing_ship and self.drawing_ship.alive:
            return self.drawing_ship
        best: Ship | None = None
        best_dist = COLLISION_DIST
        for ship in self.ships:
            if not ship.alive:
                continue
            d = math.hypot(ship.x - mx, ship.y - my)
            if d < best_dist:
                best_dist = d
                best = ship
        return best

    def _start_drawing(self, ship: Ship, mx: int, my: int) -> None:
        self.drawing = True
        self.drawing_ship = ship
        self.drawing_path = [(mx, my)]
        self._drawing_frame_counter = 0

    def _add_waypoint(self, mx: int, my: int) -> None:
        mx = max(0, min(SCREEN_W - 1, mx))
        my = max(0, min(SCREEN_H - 1, my))
        self.drawing_path.append((mx, my))

    def _finish_drawing(self) -> None:
        if not self.drawing_ship or not self.drawing_ship.alive:
            self.drawing = False
            self.drawing_ship = None
            self.drawing_path.clear()
            return

        runway = self.runways[self.drawing_ship.target_runway]
        self.drawing_ship.path = list(self.drawing_path)
        self.drawing_ship.path.append((runway.cx, runway.cy))
        self.drawing_ship.path_index = 0
        self.drawing = False
        self.drawing_ship = None
        self.drawing_path.clear()

    # ---- Landing ----
    def _check_landings(self) -> list[tuple[Ship, Runway]]:
        landed: list[tuple[Ship, Runway]] = []
        for ship in self.ships:
            if not ship.alive:
                continue
            runway = self.runways[ship.target_runway]
            if math.hypot(ship.x - runway.cx, ship.y - runway.cy) < LANDING_DIST:
                landed.append((ship, runway))
        return landed

    def _process_landing(self, ship: Ship, runway: Runway) -> int:
        ship.alive = False
        self.landings += 1
        is_match = ship.color == runway.color

        if self.surge_timer > 0:
            is_match = True

        if is_match:
            self._update_combo(correct=True)
            gained = 100 * self.combo
            if self.surge_timer > 0:
                gained *= 2
            self.score += gained
            self._spawn_landing_particles(ship.x, ship.y, runway.color)
            self._spawn_floating_text(
                ship.x, ship.y - 8, f"+{gained}", pyxel.COLOR_LIME
            )
            if self.combo > 1:
                self._spawn_floating_text(
                    ship.x,
                    ship.y - 18,
                    f"COMBO x{self.combo}",
                    pyxel.COLOR_YELLOW,
                )
            if not self.surge_timer and self.combo >= 5:
                self._activate_surge()
        else:
            self._update_combo(correct=False)
            self.score = max(0, self.score - 50)
            self.mislands += 1
            self._spawn_landing_particles(ship.x, ship.y, pyxel.COLOR_RED)
            self._spawn_floating_text(
                ship.x, ship.y - 8, "MISS", pyxel.COLOR_RED
            )

        return gained if is_match else -50

    # ---- Collision ----
    def _check_collisions(self) -> list[tuple[Ship, Ship]]:
        pairs: list[tuple[Ship, Ship]] = []
        alive = [s for s in self.ships if s.alive]
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                a, b = alive[i], alive[j]
                if math.hypot(a.x - b.x, a.y - b.y) < COLLISION_DIST:
                    pairs.append((a, b))
        return pairs

    def _process_collision(self, a: Ship, b: Ship) -> None:
        a.alive = False
        b.alive = False
        self.collisions += 1
        self._update_combo(correct=False)
        self.score = max(0, self.score - 100)

        mx = (a.x + b.x) / 2
        my = (a.y + b.y) / 2
        self._spawn_collision_particles(mx, my, a.color, b.color)
        self._spawn_floating_text(mx, my - 8, "CRASH", pyxel.COLOR_WHITE)

    # ---- COMBO / SURGE ----
    def _update_combo(self, *, correct: bool) -> None:
        if correct:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
        else:
            if self.surge_timer > 0:
                self.surge_timer = 0
            self.combo = 0

    def _activate_surge(self) -> None:
        self.surge_timer = SURGE_DURATION
        self._spawn_floating_text(
            SCREEN_W // 2, SCREEN_H // 2 - 20, "SURGE!", pyxel.COLOR_YELLOW
        )

    def _update_surge(self) -> None:
        if self.surge_timer > 0:
            self.surge_timer -= 1
            if self.surge_timer <= 0:
                self.surge_timer = 0
                self.combo = 0

    # ---- Particles ----
    def _spawn_landing_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=PARTICLE_LIFE,
                    color=color,
                )
            )

    def _spawn_collision_particles(
        self, x: float, y: float, color_a: int, color_b: int
    ) -> None:
        for _ in range(6):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=PARTICLE_LIFE,
                    color=color_a,
                )
            )
        for _ in range(6):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=PARTICLE_LIFE,
                    color=color_b,
                )
            )

    def _spawn_surge_particle(self) -> None:
        x = self.rng.uniform(0, SCREEN_W)
        y = self.rng.uniform(0, SCREEN_H)
        color = self.rng.choice(RAINBOW)
        self.particles.append(
            Particle(
                x=x, y=y, vx=0, vy=-0.3, life=PARTICLE_LIFE, color=color, size=2
            )
        )

    def _update_particles(self) -> None:
        dead: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                dead.append(p)
        for p in dead:
            self.particles.remove(p)

    # ---- Floating Text ----
    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=FLOAT_TEXT_LIFE, color=color)
        )

    def _update_floating_texts(self) -> None:
        dead: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                dead.append(ft)
        for ft in dead:
            self.floating_texts.remove(ft)

    # ---- Cleanup ----
    def _remove_dead_ships(self) -> None:
        self.ships = [s for s in self.ships if s.alive]

    # ---- Update ----
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        self._handle_drawing_input(
            is_click=pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT),
            is_held=pyxel.btn(pyxel.MOUSE_BUTTON_LEFT),
            is_released=pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT),
            mouse_x=pyxel.mouse_x,
            mouse_y=pyxel.mouse_y,
        )

        self._try_spawn()
        self._update_surge()

        for ship in self.ships:
            self._update_ship(ship, self.runways[ship.target_runway])

        landed = self._check_landings()
        for ship, runway in landed:
            self._process_landing(ship, runway)

        collisions = self._check_collisions()
        for a, b in collisions:
            if a.alive and b.alive:
                self._process_collision(a, b)

        self._remove_dead_ships()
        self._update_particles()
        self._update_floating_texts()

        if self.surge_timer > 0 and pyxel.frame_count % 10 == 0:
            for _ in range(3):
                self._spawn_surge_particle()

        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER

    def _handle_drawing_input(
        self,
        *,
        is_click: bool,
        is_held: bool,
        is_released: bool,
        mouse_x: int,
        mouse_y: int,
    ) -> None:
        if is_click and not self.drawing:
            ship = self._find_ship_at(mouse_x, mouse_y)
            if ship is not None:
                self._start_drawing(ship, mouse_x, mouse_y)
            return

        if is_held and self.drawing:
            self._drawing_frame_counter += 1
            if self._drawing_frame_counter >= WAYPOINT_RECORD_INTERVAL:
                self._drawing_frame_counter = 0
                self._add_waypoint(mouse_x, mouse_y)
            return

        if is_released and self.drawing:
            self._finish_drawing()
            return

    # ---- Draw ----
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "CHROMA ROUTE"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 30, title, pyxel.COLOR_WHITE)

        instructions = [
            "PRESS ENTER TO START",
            "",
            "CLICK-DRAG on ships to draw flight paths",
            "Route ships to matching-color runways",
            "",
            "Same-color consecutive landings = COMBO",
            "COMBO x5 = SURGE! (all match, x2 score)",
            "Wrong color = COMBO break",
            "Collision = COMBO break + penalty",
            "",
            "Survive 90s, maximize score!",
        ]
        y = 55
        for line in instructions:
            pyxel.text(SCREEN_W // 2 - len(line) * 2, y, line, pyxel.COLOR_GRAY)
            y += 10

        self._draw_runways()
        self._draw_sample_ships()

    def _draw_sample_ships(self) -> None:
        x_positions = [60, 120, 180, 240]
        for i, color in enumerate(SHIP_COLORS):
            pyxel.circ(x_positions[i], 200, SHIP_RADIUS, color)
            pyxel.circb(x_positions[i], 200, SHIP_RADIUS, pyxel.COLOR_WHITE)

    def _draw_game(self) -> None:
        self._draw_grid()
        self._draw_runways()
        self._draw_all_ship_paths()
        self._draw_ships()
        self._draw_drawing_preview()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_surge_border()
        self._draw_hud()

    def _draw_grid(self) -> None:
        for x in range(40, SCREEN_W, 40):
            pyxel.line(x, 0, x, SCREEN_H, pyxel.COLOR_NAVY)
        for y in range(40, SCREEN_H, 40):
            pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_NAVY)

    def _draw_runways(self) -> None:
        for rwy in self.runways:
            dim_color = RUNWAY_DIM.get(rwy.color, rwy.color)
            has_ship_nearby = any(
                s.alive
                and s.target_runway == self.runways.index(rwy)
                and math.hypot(s.x - rwy.cx, s.y - rwy.cy) < 60
                for s in self.ships
            )
            fill = rwy.color if has_ship_nearby else dim_color
            pyxel.rect(rwy.x, rwy.y, rwy.w, rwy.h, fill)
            pyxel.rectb(rwy.x, rwy.y, rwy.w, rwy.h, pyxel.COLOR_WHITE)

            color_char = {pyxel.COLOR_RED: "R", pyxel.COLOR_GREEN: "G",
                          pyxel.COLOR_LIGHT_BLUE: "B", pyxel.COLOR_YELLOW: "Y"}
            label = color_char.get(rwy.color, "?")
            lx = int(rwy.cx - 2)
            ly = int(rwy.cy - 3)
            pyxel.text(lx, ly, label, pyxel.COLOR_WHITE)

    def _draw_ships(self) -> None:
        for ship in self.ships:
            if not ship.alive:
                continue
            sx, sy = int(ship.x), int(ship.y)
            pyxel.circ(sx, sy, SHIP_RADIUS, ship.color)
            pyxel.circb(sx, sy, SHIP_RADIUS, pyxel.COLOR_WHITE)

            if self.drawing and ship is self.drawing_ship:
                pulse = pyxel.frame_count % 30 < 15
                if pulse:
                    pyxel.circb(sx, sy, SHIP_RADIUS + 2, pyxel.COLOR_YELLOW)

    def _draw_all_ship_paths(self) -> None:
        for ship in self.ships:
            if not ship.alive:
                continue
            if self.drawing and ship is self.drawing_ship:
                continue
            if not ship.path:
                continue
            self._draw_path_line(ship, ship.path, ship.path_index)

    @staticmethod
    def _draw_path_line(
        ship: Ship,
        path: list[tuple[float, float]],
        path_index: int,
    ) -> None:
        color = ship.color
        dim_color = pyxel.COLOR_GRAY

        if path_index < len(path):
            px, py = path[path_index]
            pyxel.line(int(ship.x), int(ship.y), int(px), int(py), color)
            for i in range(path_index, len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                pyxel.line(int(x1), int(y1), int(x2), int(y2), color)

        for i in range(min(path_index, len(path)) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            pyxel.line(int(x1), int(y1), int(x2), int(y2), dim_color)

    def _draw_drawing_preview(self) -> None:
        if not self.drawing or not self.drawing_path:
            return
        color = pyxel.COLOR_WHITE
        if self.drawing_ship:
            color = self.drawing_ship.color

        pts = self.drawing_path
        if len(pts) == 1:
            px, py = pts[0]
            pyxel.pset(int(px), int(py), color)
        else:
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                pyxel.line(int(x1), int(y1), int(x2), int(y2), color)

        mouse_pos = (pyxel.mouse_x, pyxel.mouse_y)
        if pts:
            lx, ly = pts[-1]
            pyxel.line(int(lx), int(ly), mouse_pos[0], mouse_pos[1], pyxel.COLOR_YELLOW)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE
            col = p.color if alpha > 0.5 else pyxel.COLOR_GRAY
            px, py_i = int(p.x), int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py_i < SCREEN_H:
                pyxel.rect(px, py_i, p.size, p.size, col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.color == pyxel.COLOR_YELLOW and ft.text == "SURGE!":
                col = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            else:
                col = ft.color
            x = int(ft.x - len(ft.text) * 2)
            y = int(ft.y)
            pyxel.text(x, y, ft.text, col)

    def _draw_surge_border(self) -> None:
        if self.surge_timer <= 0:
            return

        visible = pyxel.frame_count % 20 < 12
        if not visible:
            return

        offset = (pyxel.frame_count // 4) % len(RAINBOW)
        for i in range(4):
            col = RAINBOW[(offset + i) % len(RAINBOW)]
            if i == 0:
                pyxel.line(0, 0, SCREEN_W - 1, 0, col)
            elif i == 1:
                pyxel.line(SCREEN_W - 1, 0, SCREEN_W - 1, SCREEN_H - 1, col)
            elif i == 2:
                pyxel.line(SCREEN_W - 1, SCREEN_H - 1, 0, SCREEN_H - 1, col)
            else:
                pyxel.line(0, SCREEN_H - 1, 0, 0, col)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)

        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            combo_col = (
                pyxel.COLOR_YELLOW if self.combo >= 3 else pyxel.COLOR_WHITE
            )
            pyxel.text(
                SCREEN_W // 2 - len(combo_text) * 2, 4, combo_text, combo_col
            )

        if self.surge_timer > 0:
            surge_text = f"SURGE: {self.surge_timer // FPS + 1}s"
            pyxel.text(
                SCREEN_W // 2 - len(surge_text) * 2,
                16,
                surge_text,
                pyxel.COLOR_YELLOW,
            )

        time_sec = self.timer // FPS
        timer_text = f"TIME: {time_sec}s"
        timer_col = pyxel.COLOR_RED if time_sec <= 10 else pyxel.COLOR_WHITE
        pyxel.text(
            SCREEN_W - len(timer_text) * 4 - 4, 4, timer_text, timer_col
        )

        if self.drawing:
            pyxel.text(4, SCREEN_H - 10, "DRAWING PATH...", pyxel.COLOR_YELLOW)

    def _draw_game_over(self) -> None:
        bx = SCREEN_W // 2 - 80
        by = SCREEN_H // 2 - 55
        bw = 160
        bh = 110
        pyxel.rect(bx, by, bw, bh, pyxel.COLOR_BLACK)
        pyxel.rectb(bx, by, bw, bh, pyxel.COLOR_WHITE)

        lines = [
            ("GAME OVER", pyxel.COLOR_RED),
            ("", pyxel.COLOR_WHITE),
            (f"SCORE: {self.score}", pyxel.COLOR_YELLOW),
            (f"MAX COMBO: {self.max_combo}", pyxel.COLOR_WHITE),
            (f"LANDINGS: {self.landings}", pyxel.COLOR_WHITE),
            (f"MISLANDS: {self.mislands}", pyxel.COLOR_WHITE),
            (f"CRASHES: {self.collisions}", pyxel.COLOR_WHITE),
            ("", pyxel.COLOR_WHITE),
            ("PRESS ENTER TO RESTART", pyxel.COLOR_GRAY),
        ]
        y = SCREEN_H // 2 - 45
        for text, col in lines:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, col)
            y += 12


if __name__ == "__main__":
    Game()
