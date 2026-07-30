from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ============================================================
# Constants
# ============================================================

WIDTH = 320
HEIGHT = 240
BIKE_X = 60
RING_RADIUS = 20
JUMP_VELOCITY = -7.5
GRAVITY = 0.4
SCROLL_SPEED_INITIAL = 2.0
SCROLL_SPEED_MAX = 5.0
GAME_DURATION = 1800
SUPER_MOTO_DURATION = 300
COMBO_THRESHOLD = 4
HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_CRASH = 25.0
HEAT_DECAY = 0.05
STUN_MISMATCH = 15
STUN_CRASH = 20
BIKE_COLOR_CYCLE = 20
GHOST_RECORD_INTERVAL = 5
MATCH_SCORE_BASE = 100
MATCH_SCORE_SUPER_MULT = 3

CLR_RED = 8
CLR_LIME = 11
CLR_DARK_BLUE = 5
CLR_YELLOW = 10
CLR_CYAN = 12
CLR_WHITE = 7
CLR_BROWN = 4
CLR_NAVY = 1
CLR_LIGHT_BLUE = 6
CLR_BLACK = 0
CLR_ORANGE = 9

COMBINATION = (CLR_RED, CLR_LIME, CLR_DARK_BLUE, CLR_YELLOW)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ============================================================
# Data Classes
# ============================================================


@dataclass
class Ring:
    x: float
    y: float
    color: int
    active: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    grav: float = 0.05


@dataclass
class GhostDot:
    x: float
    y: float


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.5


# ============================================================
# Game Class
# ============================================================


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, "MOTO CHAIN", display_scale=2, fps=30)
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.timer: int = 0
        self.heat: float = 0.0
        self.bike_color_idx: int = 0
        self.bike_vy: float = 0.0
        self.bike_y: float = 0.0
        self.bike_grounded: bool = True
        self.stun_timer: int = 0
        self.super_timer: int = 0
        self.scroll_x: float = 0.0
        self.scroll_speed: float = SCROLL_SPEED_INITIAL
        self.terrain_phase: float = 0.0
        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.ghost_dots: list[GhostDot] = []
        self.best_ghost_dots: list[GhostDot] = []
        self.floating_texts: list[FloatingText] = []
        self.ring_spawn_timer: int = 0
        self.best_run: list[tuple[float, float]] = []
        self._rng: random.Random = random.Random()
        self._headless: bool = False
        self._frame_count: int = 0
        self._reset_playing()
        pyxel.run(self.update, self.draw)

    # ---- State Reset ----

    def _reset_playing(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = GAME_DURATION
        self.heat = 0.0
        self.bike_color_idx = 0
        self.bike_vy = 0.0
        self.bike_y = self._get_ground_y(self.scroll_x + BIKE_X) - 12
        self.bike_grounded = True
        self.stun_timer = 0
        self.super_timer = 0
        self.scroll_x = 0.0
        self.scroll_speed = SCROLL_SPEED_INITIAL
        self.terrain_phase = 0.0
        self.rings.clear()
        self.particles.clear()
        self.ghost_dots.clear()
        self.floating_texts.clear()
        self.ring_spawn_timer = 0
        self._frame_count = 0

    # ---- Terrain & Position ----

    def _get_ground_y(self, scroll_x: float) -> float:
        amp = 15.0 + (scroll_x / 200.0) * 10.0
        freq = 0.02
        return 180.0 + math.sin(scroll_x * freq) * amp

    def _get_bike_screen_y(self) -> float:
        return self.bike_y

    def _update_scroll(self) -> None:
        speed_ratio = 1.0 - (self.timer / GAME_DURATION)
        self.scroll_speed = SCROLL_SPEED_INITIAL + (SCROLL_SPEED_MAX - SCROLL_SPEED_INITIAL) * speed_ratio
        self.scroll_x += self.scroll_speed
        self.terrain_phase += 0.05

    def _update_terrain(self) -> None:
        pass

    # ---- Bike ----

    def _get_bike_color(self) -> int:
        if self.super_timer > 0:
            idx = (self._frame_count // 4) % 4
            return COMBINATION[idx]
        return COMBINATION[self.bike_color_idx]

    def _update_bike(self) -> None:
        if self.stun_timer > 0:
            self.stun_timer -= 1

        ground_y = self._get_ground_y(self.scroll_x + BIKE_X) - 12

        if self.super_timer > 0 and self.bike_grounded and self.stun_timer == 0:
            self.bike_vy = JUMP_VELOCITY
            self.bike_grounded = False

        self.bike_vy += GRAVITY
        self.bike_y += self.bike_vy

        if self.bike_y >= ground_y:
            if self.bike_vy > 3.0 and not self.bike_grounded:
                self._on_crash()
            self.bike_y = ground_y
            self.bike_vy = 0.0
            if self.stun_timer == 0:
                self.bike_grounded = True

        if self.super_timer == 0:
            self.bike_color_idx = (self._frame_count // BIKE_COLOR_CYCLE) % 4

    def _try_jump(self) -> None:
        if self.stun_timer > 0:
            return
        if self.bike_grounded:
            self.bike_vy = JUMP_VELOCITY
            self.bike_grounded = False

    # ---- Rings ----

    def _spawn_ring(self) -> None:
        ground_y = self._get_ground_y(self.scroll_x + WIDTH)
        min_y = max(20.0, ground_y - 120.0)
        max_y = min(220.0, ground_y - 30.0)
        if min_y >= max_y - 10:
            min_y = 40.0
            max_y = 160.0
        y = self._rng.uniform(min_y, max_y)
        color = self._rng.choice(COMBINATION)
        self.rings.append(Ring(x=self.scroll_x + WIDTH, y=y, color=color))

    def _check_ring_collision(self, ring: Ring) -> bool:
        bx = BIKE_X
        by = self.bike_y
        dist = math.hypot(bx - ring.x, by - ring.y)
        return dist < RING_RADIUS

    def _update_rings(self) -> None:
        for ring in self.rings:
            ring.x -= self.scroll_speed

        for ring in list(self.rings):
            if ring.x < self.scroll_x - RING_RADIUS:
                self.rings.remove(ring)
                continue
            if ring.active and self._check_ring_collision(ring):
                ring.active = False
                if self.super_timer > 0:
                    self._on_match_success(ring)
                elif ring.color == self._get_bike_color():
                    self._on_match_success(ring)
                else:
                    self._on_match_fail(ring)

    # ---- Combo / Match / Fail ----

    def _on_match_success(self, ring: Ring) -> None:
        base_score = MATCH_SCORE_BASE + self.combo * 50
        if self.super_timer > 0:
            base_score *= MATCH_SCORE_SUPER_MULT
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.score += base_score
        self._spawn_particles(ring.x, ring.y, 6, ring.color, "match")
        txt_color = CLR_WHITE if self.super_timer == 0 else self._get_bike_color()
        self._add_floating_text(ring.x, ring.y, f"+{base_score}", 30, txt_color)
        if self.combo >= 2:
            combo_color = CLR_YELLOW if self.super_timer == 0 else self._get_bike_color()
            self._add_floating_text(ring.x, ring.y - 12, f"COMBO x{self.combo}", 20, combo_color)
        if self.combo >= COMBO_THRESHOLD and self.super_timer == 0:
            self._trigger_super_moto()

    def _on_match_fail(self, ring: Ring) -> None:
        self.combo = 0
        if self.super_timer == 0:
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.stun_timer = max(self.stun_timer, STUN_MISMATCH)
        self._spawn_particles(ring.x, ring.y, 4, CLR_RED, "mismatch")
        label = "MISS" if self.super_timer == 0 else "?"
        self._add_floating_text(ring.x, ring.y, label, 20, CLR_RED)

    def _trigger_super_moto(self) -> None:
        self.super_timer = SUPER_MOTO_DURATION
        self._spawn_particles(BIKE_X, self.bike_y, 20, CLR_YELLOW, "super")
        self._add_floating_text(BIKE_X, self.bike_y - 16, "SUPER MOTO!", 40, CLR_YELLOW)

    # ---- Heat ----

    def _update_heat(self) -> None:
        if self.heat > 0 and self.super_timer == 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ---- Crash ----

    def _on_crash(self) -> None:
        self.combo = 0
        if self.super_timer == 0:
            self.heat = min(HEAT_MAX, self.heat + HEAT_CRASH)
        self.stun_timer = max(self.stun_timer, STUN_CRASH)
        self._spawn_particles(BIKE_X, self.bike_y, 8, CLR_ORANGE, "crash")
        self._add_floating_text(BIKE_X, self.bike_y - 10, "CRASH!", 20, CLR_ORANGE)

    # ---- Particles ----

    def _spawn_particles(self, x: float, y: float, count: int, color: int, event_type: str) -> None:
        for _ in range(count):
            if event_type == "match":
                vx = self._rng.uniform(-1.0, 1.0)
                vy = self._rng.uniform(-2.0, -1.0)
                life = 15
                grav = 0.05
            elif event_type == "super":
                c = self._rng.choice(COMBINATION)
                vx = self._rng.uniform(-3.0, 3.0)
                vy = self._rng.uniform(-3.0, -1.0)
                life = 25
                grav = 0.03
                color = c
            elif event_type == "mismatch":
                vx = self._rng.uniform(-1.0, 1.0)
                vy = self._rng.uniform(-1.0, 1.0)
                life = 10
                grav = 0.05
            elif event_type == "crash":
                vx = self._rng.uniform(-2.0, 2.0)
                vy = self._rng.uniform(-2.0, 0.0)
                life = 15
                grav = 0.1
            else:
                vx = self._rng.uniform(-1.0, 1.0)
                vy = self._rng.uniform(-2.0, -1.0)
                life = 15
                grav = 0.05
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color, grav=grav)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.grav
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ---- Floating Text ----

    def _add_floating_text(self, x: float, y: float, text: str, life: int, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ---- Ghost Trail ----

    def _record_ghost(self) -> None:
        if self._frame_count % GHOST_RECORD_INTERVAL != 0:
            return
        screen_x = BIKE_X
        screen_y = int(self.bike_y)
        self.ghost_dots.append(GhostDot(x=screen_x, y=screen_y))

    # ---- Update Dispatch ----

    def update(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if not self._headless:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.PLAYING
                self._reset_playing()

    def _update_playing(self) -> None:
        if not self._headless:
            if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_SPACE):
                self._try_jump()

        self._frame_count += 1
        self._update_scroll()
        self._update_terrain()
        self._update_bike()

        self.ring_spawn_timer -= 1
        spawn_interval = max(15, 45 - int(self.scroll_speed * 5))
        if self.ring_spawn_timer <= 0:
            self._spawn_ring()
            self.ring_spawn_timer = spawn_interval

        self._update_rings()
        self._update_particles()
        self._update_floating_texts()

        if self.super_timer > 0:
            self.super_timer -= 1

        self.timer -= 1

        # Check game-over BEFORE heat decay (heat at 100 must trigger)
        if self.heat >= HEAT_MAX:
            self._end_game()
            return
        if self.timer <= 0:
            self._end_game()
            return

        self._update_heat()
        self._record_ghost()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_ghost_dots = list(self.ghost_dots)
            self.best_run = [(BIKE_X, self.bike_y) for _ in range(1)]

    def _update_game_over(self) -> None:
        if not self._headless:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.PLAYING
                self._reset_playing()

    # ---- Draw Dispatch ----

    def draw(self) -> None:
        if self._headless:
            return
        pyxel.cls(CLR_NAVY)
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_playing()
            case Phase.GAME_OVER:
                self._draw_game_over()

    # ---- Draw Helpers ----

    def _draw_sky_and_ground(self) -> None:
        pyxel.cls(CLR_LIGHT_BLUE)
        ground_points: list[tuple[float, float]] = []
        for sx in range(0, WIDTH + 2, 2):
            wx = self.scroll_x + sx
            gy = self._get_ground_y(wx)
            ground_points.append((float(sx), gy))
        ground_poly = ground_points + [(float(WIDTH), float(HEIGHT)), (0.0, float(HEIGHT))]
        for i in range(len(ground_poly) - 1):
            pyxel.tri(
                ground_poly[i][0],
                ground_poly[i][1],
                ground_poly[i + 1][0],
                ground_poly[i + 1][1],
                0.0,
                float(HEIGHT),
                CLR_BROWN,
            )

    def _draw_bike(self) -> None:
        bx = BIKE_X
        by = int(self.bike_y)
        color = self._get_bike_color()
        pyxel.circ(bx - 8, by + 6, 3, color)
        pyxel.circ(bx + 8, by + 6, 3, color)
        pyxel.line(bx - 8, by + 6, bx, by - 4, color)
        pyxel.line(bx + 8, by + 6, bx, by - 4, color)
        pyxel.line(bx - 6, by + 1, bx + 6, by + 1, color)
        pyxel.rect(bx - 2, by - 6, 4, 6, color)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if not ring.active:
                continue
            sx = ring.x - self.scroll_x
            color = ring.color
            if self.super_timer > 0:
                color = COMBINATION[(pyxel.frame_count // 3) % 4]
            pyxel.circb(int(sx), int(ring.y), RING_RADIUS, color)
            pyxel.circb(int(sx), int(ring.y), RING_RADIUS - 1, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x - self.scroll_x) if self.phase == Phase.PLAYING else int(p.x), int(p.y), p.color)

    def _draw_ghost_trail(self) -> None:
        for dot in self.best_ghost_dots:
            pyxel.pset(int(dot.x), int(dot.y), CLR_CYAN)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            sx = int(ft.x)
            pyxel.text(sx, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", CLR_WHITE)
        combo_text = f"COMBO: {self.combo}"
        combo_x = WIDTH // 2 - len(combo_text) * 2
        pyxel.text(combo_x, 2, combo_text, CLR_YELLOW if self.combo >= COMBO_THRESHOLD else CLR_WHITE)
        secs = max(0, self.timer) // 30
        timer_text = f"TIME: {secs}"
        timer_x = WIDTH - len(timer_text) * 4 - 4
        pyxel.text(timer_x, 2, timer_text, CLR_WHITE if secs > 10 else CLR_RED)

        bar_x = timer_x
        bar_y = 14
        bar_w = len(timer_text) * 4
        bar_h = 4
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, CLR_BLACK)
        heat_w = int(bar_w * (self.heat / HEAT_MAX))
        heat_color = CLR_LIME if self.heat < 50 else CLR_YELLOW if self.heat < 75 else CLR_RED
        pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_color)

        if self.super_timer > 0:
            super_secs = self.super_timer / 30.0
            super_text = f"SUPER: {super_secs:.1f}s"
            pyxel.text(4, 16, super_text, COMBINATION[(pyxel.frame_count // 3) % 4])

    def _draw_super_border(self) -> None:
        if self.super_timer > 0:
            c = COMBINATION[(pyxel.frame_count // 4) % 4]
            pyxel.rectb(0, 0, WIDTH, HEIGHT, c)
            pyxel.rectb(1, 1, WIDTH - 2, HEIGHT - 2, c)

    # ---- Title Screen ----

    def _draw_title(self) -> None:
        pyxel.cls(CLR_NAVY)
        title = "MOTO CHAIN"
        x = WIDTH // 2 - len(title) * 4 // 2
        pyxel.text(x, 60, title, CLR_YELLOW)
        subtitle = "Color-Match Combo Racing"
        sx = WIDTH // 2 - len(subtitle) * 4 // 2
        pyxel.text(sx, 76, subtitle, CLR_WHITE)
        line1 = "SPACE or CLICK to start"
        lx = WIDTH // 2 - len(line1) * 4 // 2
        pyxel.text(lx, 120, line1, CLR_LIME)
        line2 = "UP=Jump  Color cycles automatically"
        lx2 = WIDTH // 2 - len(line2) * 4 // 2
        pyxel.text(lx2, 140, line2, CLR_CYAN)
        line3 = "Match ring color = COMBO!"
        lx3 = WIDTH // 2 - len(line3) * 4 // 2
        pyxel.text(lx3, 156, line3, CLR_WHITE)
        line4 = "COMBO x4 = SUPER MOTO (rainbow)"
        lx4 = WIDTH // 2 - len(line4) * 4 // 2
        pyxel.text(lx4, 172, line4, COMBINATION[pyxel.frame_count // 15 % 4])
        line5 = "HEAT=100 = GAME OVER"
        lx5 = WIDTH // 2 - len(line5) * 4 // 2
        pyxel.text(lx5, 188, line5, CLR_RED)

    # ---- Playing Screen ----

    def _draw_playing(self) -> None:
        self._draw_sky_and_ground()
        self._draw_ghost_trail()
        self._draw_rings()
        for p in self.particles:
            pyxel.pset(int(p.x - self.scroll_x), int(p.y), p.color)
        self._draw_bike()
        self._draw_hud()
        self._draw_floating_texts()
        self._draw_super_border()

    # ---- Game Over Screen ----

    def _draw_game_over(self) -> None:
        pyxel.cls(CLR_NAVY)
        go_text = "GAME OVER"
        gx = WIDTH // 2 - len(go_text) * 4 // 2
        pyxel.text(gx, 70, go_text, CLR_RED)
        score_text = f"SCORE: {self.score}"
        sx = WIDTH // 2 - len(score_text) * 4 // 2
        pyxel.text(sx, 100, score_text, CLR_WHITE)
        best_text = f"BEST: {self.best_score}"
        bx = WIDTH // 2 - len(best_text) * 4 // 2
        pyxel.text(bx, 114, best_text, CLR_YELLOW)
        combo_text = f"MAX COMBO: {self.max_combo}"
        cx = WIDTH // 2 - len(combo_text) * 4 // 2
        pyxel.text(cx, 130, combo_text, CLR_LIME)
        retry_text = "SPACE or CLICK to retry"
        rx = WIDTH // 2 - len(retry_text) * 4 // 2
        pyxel.text(rx, 170, retry_text, CLR_WHITE)

    # ---- Run ----

    def run(self) -> None:
        pass


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
