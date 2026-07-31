"""MAGNET LIFT — Scrapyard Magnetic Crane Arcade Action"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_DURATION = 1800

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

SCRAP_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
SCRAP_SIZE = 12

CRANE_Y = 20
CRANE_MIN_X = 40
CRANE_MAX_X = 280
CRANE_SPEED = 3.0
CRANE_SPEED_MAGNET = 1.5

CONVEYOR_TOP = 40
CONVEYOR_BOTTOM = 240
CONVEYOR_LINE_SPACING = 20

MAGNET_EXTEND_SPEED = 4.0
MAGNET_RETRACT_SPEED = 6.0
MAGNET_WIDTH = 8

SUPER_THRESHOLD = 4
SUPER_DURATION = 300

HEAT_MISMATCH = 15.0
HEAT_MISS = 5.0
HEAT_DECAY = 0.02
HEAT_CAP = 100.0

SPAWN_INTERVAL_START = 60
SPAWN_INTERVAL_END = 25
SCROLL_SPEED_START = 1.0
SCROLL_SPEED_END = 3.0

TRAIL_LIFE = 60
SHAKE_PICKUP = 10
SHAKE_GAMEOVER = 15

PARTICLE_GRAVITY = 0.08
PARTICLE_FRICTION = 0.99


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Scrap:
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


@dataclass
class TrailDot:
    x: float
    y: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    SCRAP_COLORS: ClassVar[tuple[int, ...]] = SCRAP_COLORS

    def __new__(cls, headless: bool = False) -> Game:
        obj = object.__new__(cls)
        obj._set_defaults()
        obj._headless = headless
        return obj

    def _set_defaults(self) -> None:
        self._headless: bool = False
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.super_timer: int = 0
        self.crane_x: float = 160.0
        self.magnet_y: float = float(CRANE_Y)
        self.magnet_extending: bool = False
        self.magnet_retracting: bool = False
        self.last_color: int = -1
        self.space_was_held: bool = False
        self.scraps: list[Scrap] = []
        self.particles: list[Particle] = []
        self.trails: list[TrailDot] = []
        self.floating_texts: list[FloatingText] = []
        self.spawn_timer: int = 0
        self.spawn_interval: int = SPAWN_INTERVAL_START
        self.scroll_speed: float = SCROLL_SPEED_START
        self.shake_frames: int = 0
        self.shake_intensity: float = 0.0
        self.frame: int = 0
        self._rng: random.Random = random.Random()

    def __init__(self, headless: bool = False) -> None:
        if not headless:
            pyxel.init(SCREEN_W, SCREEN_H, title="Magnet Lift", fps=FPS)
            self.reset()
            pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.crane_x = 160.0
        self.magnet_y = float(CRANE_Y)
        self.magnet_extending = False
        self.magnet_retracting = False
        self.last_color = -1
        self.space_was_held = False
        self.scraps.clear()
        self.particles.clear()
        self.trails.clear()
        self.floating_texts.clear()
        self.spawn_timer = 30
        self.spawn_interval = SPAWN_INTERVAL_START
        self.scroll_speed = SCROLL_SPEED_START
        self.shake_frames = 0
        self.shake_intensity = 0.0
        self.frame = 0

    def reset_for_playing(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.crane_x = 160.0
        self.magnet_y = float(CRANE_Y)
        self.magnet_extending = False
        self.magnet_retracting = False
        self.last_color = -1
        self.space_was_held = False
        self.scraps.clear()
        self.particles.clear()
        self.trails.clear()
        self.floating_texts.clear()
        self.spawn_timer = 30
        self.spawn_interval = SPAWN_INTERVAL_START
        self.scroll_speed = SCROLL_SPEED_START
        self.shake_frames = 0
        self.shake_intensity = 0.0
        self.frame = 0

    # ── Input ────────────────────────────────────────────────────────────

    def _get_input(self) -> dict:
        if self._headless:
            return {
                "left": False,
                "right": False,
                "space": False,
                "space_p": False,
                "return_p": False,
            }
        return {
            "left": pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A),
            "right": pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D),
            "space": pyxel.btn(pyxel.KEY_SPACE) or pyxel.btn(pyxel.KEY_DOWN),
            "space_p": pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_DOWN),
            "return_p": pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN),
        }

    # ── Update ────────────────────────────────────────────────────────────

    def _update(self) -> None:
        inp = self._get_input()

        if self.phase == Phase.TITLE:
            self._update_title(inp)
        elif self.phase == Phase.PLAYING:
            self._update_playing(inp)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(inp)

    def _update_title(self, inp: dict) -> None:
        if inp["space_p"] or inp["return_p"]:
            self.reset_for_playing()
            self.phase = Phase.PLAYING

    def _update_playing(self, inp: dict) -> None:
        self.frame += 1

        self._update_crane(inp)
        self._update_magnet(inp)
        self._update_scraps()
        self._update_spawn()
        self._update_difficulty()
        self._update_particles()
        self._update_trails()
        self._update_floating_texts()
        self._update_heat()
        self._update_super()

        if self.shake_frames > 0:
            self.shake_frames -= 1
            if self.shake_frames == 0:
                self.shake_intensity = 0.0

        self.timer -= 1
        if self.timer <= 0 and self.phase == Phase.PLAYING:
            self._end_game()

    def _update_crane(self, inp: dict) -> None:
        speed = CRANE_SPEED_MAGNET if (self.magnet_extending or self.magnet_retracting) else CRANE_SPEED
        if inp["left"]:
            self.crane_x -= speed
        if inp["right"]:
            self.crane_x += speed
        self.crane_x = max(CRANE_MIN_X, min(CRANE_MAX_X, self.crane_x))

    def _update_magnet(self, inp: dict) -> None:
        space_held = inp["space"]
        if space_held and not self.space_was_held:
            self.magnet_extending = True
            self.magnet_retracting = False
        elif not space_held and self.space_was_held:
            self.magnet_retracting = True
            self.magnet_extending = False
        self.space_was_held = space_held

        if self.magnet_extending:
            self.magnet_y += MAGNET_EXTEND_SPEED
            if self.magnet_y >= CONVEYOR_BOTTOM - SCRAP_SIZE:
                self.magnet_y = float(CONVEYOR_BOTTOM - SCRAP_SIZE)
                self.magnet_extending = False
            self._check_all_pickups()

        if self.magnet_retracting:
            self.magnet_y -= MAGNET_RETRACT_SPEED
            if self.magnet_y <= CRANE_Y:
                self.magnet_y = float(CRANE_Y)
                self.magnet_retracting = False

    def _check_all_pickups(self) -> None:
        for scrap in self.scraps:
            if scrap.collected:
                continue
            if self._check_pickup(scrap):
                scrap.collected = True
                self._handle_pickup(scrap)
                return

    def _check_pickup(self, scrap: Scrap) -> bool:
        half = MAGNET_WIDTH / 2
        magnet_left = self.crane_x - half
        magnet_right = self.crane_x + half
        magnet_top = self.magnet_y
        magnet_bottom = self.magnet_y + MAGNET_WIDTH

        scrap_half = SCRAP_SIZE / 2
        scrap_left = scrap.x - scrap_half
        scrap_right = scrap.x + scrap_half
        scrap_top = scrap.y - scrap_half
        scrap_bottom = scrap.y + scrap_half

        return (
            magnet_right > scrap_left
            and magnet_left < scrap_right
            and magnet_bottom > scrap_top
            and magnet_top < scrap_bottom
        )

    def _handle_pickup(self, scrap: Scrap) -> None:
        color = scrap.color
        matched = self._is_super() or (self.last_color == -1 or self.last_color == color)

        if matched:
            self.last_color = color
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._score_value(self.combo)
            if self._is_super():
                points *= 3
            self.score += points

            self._spawn_particles(scrap.x, scrap.y, color, 12)
            self._spawn_floating_text(scrap.x, scrap.y - 10, f"+{points}", LIME, 30)
            self.trails.append(TrailDot(x=scrap.x, y=scrap.y, life=TRAIL_LIFE, color=color))

            if self.combo >= SUPER_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                self.shake_frames = SHAKE_PICKUP
                self.shake_intensity = 3.0
                self._spawn_particles(scrap.x, scrap.y, -1, 30)
                self._spawn_floating_text(scrap.x, scrap.y - 22, "SUPER MAGNET!", YELLOW, 40)
        else:
            self.combo = 0
            self.last_color = color
            self.heat = min(HEAT_CAP, self.heat + HEAT_MISMATCH)
            self._spawn_particles(scrap.x, scrap.y, GRAY, 8)
            self._spawn_floating_text(scrap.x, scrap.y - 10, "MISS!", RED, 25)

    def _update_scraps(self) -> None:
        missed_any = False
        for scrap in self.scraps:
            if not scrap.collected:
                scrap.y -= self.scroll_speed
                if scrap.y < CONVEYOR_TOP - SCRAP_SIZE:
                    scrap.collected = True
                    missed_any = True
        if missed_any:
            self.heat = min(HEAT_CAP, self.heat + HEAT_MISS)
        self.scraps = [s for s in self.scraps if not (s.collected and s.y < CONVEYOR_TOP - SCRAP_SIZE * 2)]
        self.scraps = [s for s in self.scraps if s.y > CONVEYOR_TOP - SCRAP_SIZE or not s.collected]

    def _update_spawn(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.scraps.append(self._spawn_scrap())
            self.spawn_timer = self.spawn_interval

    def _update_difficulty(self) -> None:
        elapsed = GAME_DURATION - self.timer
        t = elapsed / GAME_DURATION
        self.scroll_speed = SCROLL_SPEED_START + (SCROLL_SPEED_END - SCROLL_SPEED_START) * t
        self.spawn_interval = int(SPAWN_INTERVAL_START - (SPAWN_INTERVAL_START - SPAWN_INTERVAL_END) * t)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += PARTICLE_GRAVITY
            p.vx *= PARTICLE_FRICTION
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_trails(self) -> None:
        for t in self.trails:
            t.life -= 1
        self.trails = [t for t in self.trails if t.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_heat(self) -> None:
        if self.heat >= HEAT_CAP:
            self._end_game()
            return
        if not self._is_super():
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0
                self.last_color = -1

    def _end_game(self) -> None:
        if self.score > self.best_score:
            self.best_score = self.score
        self.shake_frames = SHAKE_GAMEOVER
        self.shake_intensity = 5.0
        self._spawn_particles(SCREEN_W // 2, SCREEN_H // 2, RED, 50)
        self.phase = Phase.GAME_OVER

    # ── Spawning ──────────────────────────────────────────────────────────

    def _spawn_scrap(self) -> Scrap:
        color = self._rng.choice(SCRAP_COLORS)
        x = self._rng.uniform(float(CRANE_MIN_X + SCRAP_SIZE), float(CRANE_MAX_X - SCRAP_SIZE))
        y = float(CONVEYOR_BOTTOM + SCRAP_SIZE)
        return Scrap(x=x, y=y, color=color)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            pcolor = color if color != -1 else self._rng.choice(SCRAP_COLORS)
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(20, 40) if color == -1 else (
                self._rng.randint(15, 25) if color != GRAY else self._rng.randint(10, 20)
            )
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=pcolor))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    # ── Logic helpers ─────────────────────────────────────────────────────

    def _is_super(self) -> bool:
        return self.super_timer > 0

    @staticmethod
    def _color_for_index(idx: int) -> int:
        return SCRAP_COLORS[idx % len(SCRAP_COLORS)]

    @staticmethod
    def _score_value(combo: int) -> int:
        return 10 + combo * 5

    # ── Game over ─────────────────────────────────────────────────────────

    def _update_game_over(self, inp: dict) -> None:
        self.frame += 1
        self._update_particles()
        if self.shake_frames > 0:
            self.shake_frames -= 1
            if self.shake_frames == 0:
                self.shake_intensity = 0.0
        if inp["space_p"] or inp["return_p"]:
            self.reset()
            self.phase = Phase.TITLE

    # ── Draw ──────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        sx, sy = 0, 0
        if self.shake_frames > 0:
            sx = self._rng.randint(-int(self.shake_intensity), int(self.shake_intensity))
            sy = self._rng.randint(-int(self.shake_intensity), int(self.shake_intensity))
            try:
                pyxel.camera(sx, sy)
            except BaseException:
                pass

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_conveyor()
            self._draw_trails()
            self._draw_scraps()
            self._draw_magnet()
            self._draw_crane()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_hud()
            if self._is_super():
                self._draw_super_border()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        pyxel.text(SCREEN_W // 2 - 42, 60, "MAGNET LIFT", WHITE)
        pyxel.text(SCREEN_W // 2 - 46, 80, "SCRAPYARD CRANE", LIME)
        pyxel.text(SCREEN_W // 2 - 58, 108, "LEFT/RIGHT or A/D: Move crane", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 120, "SPACE or DOWN: Lower magnet", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 132, "Release: Retract magnet", WHITE)
        pyxel.text(SCREEN_W // 2 - 62, 150, "Same color x4 = SUPER MAGNET!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 62, 162, "Wrong color: COMBO reset + HEAT", RED)
        pyxel.text(SCREEN_W // 2 - 62, 174, "Miss scrap: HEAT penalty", GRAY)
        pyxel.text(SCREEN_W // 2 - 46, 192, "HEAT 100  = GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 58, 208, "60s to score as high as you can!", WHITE)
        pyxel.text(SCREEN_W // 2 - 48, 228, "SPACE to start", CYAN)
        if self.best_score > 0:
            pyxel.text(SCREEN_W // 2 - 30, 238, f"BEST: {self.best_score}", YELLOW)

    def _draw_conveyor(self) -> None:
        pyxel.rect(0, CONVEYOR_TOP, SCREEN_W, CONVEYOR_BOTTOM - CONVEYOR_TOP, GRAY)
        for y in range(CONVEYOR_TOP + 5, CONVEYOR_BOTTOM, CONVEYOR_LINE_SPACING):
            offset = (self.frame * int(self.scroll_speed)) % CONVEYOR_LINE_SPACING
            pyxel.line(0, y + offset, SCREEN_W, y + offset, BROWN)

    def _draw_crane(self) -> None:
        cy = int(CRANE_Y)
        pyxel.rect(0, cy - 3, SCREEN_W, 8, DARK_BLUE)
        rail_y_offset = self.frame % 4
        for i in range(0, SCREEN_W, 12):
            pyxel.rect(i + rail_y_offset, cy - 1, 4, 2, LIGHT_BLUE)

    def _draw_magnet(self) -> None:
        hx = int(self.crane_x)
        my = int(self.magnet_y)

        if self._is_super():
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            line_color = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            magnet_color = rainbow[(pyxel.frame_count // 4) % len(rainbow)]
        else:
            line_color = DARK_BLUE
            magnet_color = DARK_BLUE

        pyxel.line(hx, CRANE_Y, hx, my, line_color)

        mw = MAGNET_WIDTH
        mh = MAGNET_WIDTH + 2
        pyxel.rect(hx - mw // 2, my, mw, mh, magnet_color)
        pyxel.rectb(hx - mw // 2, my, mw, mh, WHITE)

    def _draw_trails(self) -> None:
        for t in self.trails:
            alpha = t.life / TRAIL_LIFE
            radius = max(1, int(3 * alpha))
            pyxel.circ(int(t.x), int(t.y), radius, t.color)

    def _draw_scraps(self) -> None:
        for scrap in self.scraps:
            if scrap.collected:
                continue
            half = SCRAP_SIZE // 2
            x = int(scrap.x - half)
            y = int(scrap.y - half)
            pyxel.rect(x, y, SCRAP_SIZE, SCRAP_SIZE, scrap.color)
            pyxel.rectb(x, y, SCRAP_SIZE, SCRAP_SIZE, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 6:
                pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
            else:
                pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 12, f"COMBO: {self.combo}", YELLOW if self.combo >= 3 else WHITE)
        pyxel.text(4, 22, f"MAX: {self.max_combo}", LIME)

        secs = max(0, self.timer // FPS)
        timer_color = WHITE
        if secs <= 10:
            timer_color = RED
        elif secs <= 20:
            timer_color = ORANGE
        pyxel.text(SCREEN_W // 2 - 24, 2, f"TIME: {secs}s", timer_color)

        pyxel.text(SCREEN_W // 2 - 24, 14, "HEAT", WHITE)
        heat_w = 60
        heat_h = 6
        heat_x = SCREEN_W // 2 - 24
        pyxel.rectb(heat_x, 22, heat_w, heat_h, WHITE)
        heat_fill = int(heat_w * self.heat / HEAT_CAP)
        if self.heat <= 40:
            heat_color = LIME
        elif self.heat <= 70:
            heat_color = YELLOW
        elif self.heat <= 90:
            heat_color = ORANGE
        else:
            heat_color = RED
        pyxel.rect(heat_x, 22, heat_fill, heat_h, heat_color)

        if self._is_super():
            super_secs = self.super_timer // FPS
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            col = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            pyxel.text(SCREEN_W - 80, 2, f"SUPER! {super_secs}s", col)
            pyxel.text(SCREEN_W - 80, 14, "3x SCORE", YELLOW)

    def _draw_super_border(self) -> None:
        rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
        idx = (pyxel.frame_count // 4) % len(rainbow)
        col = rainbow[idx]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, col)
        idx2 = (idx + 3) % len(rainbow)
        col2 = rainbow[idx2]
        if pyxel.frame_count % 8 < 4:
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, col2)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 40, 140, 70, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 40, 140, 70, RED)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 30, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 - 15, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 45, SCREEN_H // 2 - 3, f"MAX COMBO: {self.max_combo}", LIME)
        if self.score >= self.best_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 25, SCREEN_H // 2 + 9, "NEW BEST!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 22, "SPACE to retry", CYAN)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
