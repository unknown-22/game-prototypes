"""TEA CHAIN - a tea ceremony chain-combo arcade prototype.

Read the guests' order, wait for your brew to steep (higher multiplier),
and serve matching colors to build combos into a rainbow SUPER BREW.
Do not over-steep, and do not keep guests waiting.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

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

TEA_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
TEA_NAMES = ("HIBISCUS", "MATCHA", "OOLONG", "CHAMOMILE")
TEA_ABBR = ("HIB", "MAT", "OOL", "CHA")

STEEP_MAX = 45
MAX_HEAT = 100.0
PATIENCE_MAX = 600
SUPER_DURATION = 300
GAME_TIME = 3600
DECAY = 0.02

SEAT_X = (70, 160, 250)
SEAT_Y = 70
MASTER_X = 290


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Guest:
    seat: int
    color: int
    patience: int


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
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="Tea Chain", fps=60, display_scale=2)
        self.rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.steep = 0
        self.brew_color = 0
        self.color_timer = 20
        self.spawn_timer = 90
        self.super_timer = 0
        self.shake_frames = 0
        self.guests: list[Guest] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatText] = []

    # ------------------------------------------------------------------ #
    # Core logic (testable, no pyxel input)                              #
    # ------------------------------------------------------------------ #

    def serve(self, seat: int) -> str:
        if self.phase != Phase.PLAYING:
            return "empty"
        guest = next((g for g in self.guests if g.seat == seat), None)
        if guest is None:
            return "empty"

        super_active = self.super_timer > 0
        if self.brew_color == guest.color or super_active:
            steep_mult = 1 + self.steep // 15
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = steep_mult * (3 if super_active else 1)
            gained = 10 * self.combo * mult
            self.score += gained
            self.steep = 0
            self.guests.remove(guest)
            self._spawn_match_particles(guest.seat, super_active)
            self.floating_texts.append(
                FloatText(SEAT_X[seat], SEAT_Y - 20, f"+{gained}", 30, WHITE)
            )
            if self.combo >= 4 and not super_active:
                self.super_timer = SUPER_DURATION
                self.floating_texts.append(
                    FloatText(WIDTH // 2 - 40, 60, "SUPER BREW!", 60, YELLOW)
                )
            return "match"

        self.heat += 15.0
        self.combo = 0
        self.steep = 0
        self.shake_frames = 6
        self._burst(SEAT_X[seat], SEAT_Y, RED, 4, 1.0, -1.0, 1.0, 15)
        self.floating_texts.append(
            FloatText(SEAT_X[seat], SEAT_Y - 20, "WRONG!", 40, RED)
        )
        self._check_game_over()
        return "wrong"

    def _update_steep(self) -> None:
        self.steep += 1
        if self.steep >= STEEP_MAX:
            self.heat += 12.0
            self.steep = 0
            self.shake_frames = 6
            self._burst(MASTER_X, 100, CYAN, 4, 1.0, -1.0, 1.0, 15)
            self.floating_texts.append(
                FloatText(MASTER_X - 16, 80, "BITTER!", 40, CYAN)
            )
            self._check_game_over()

    def _update_brew_color(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.brew_color = (self.brew_color + 1) % 4
            elapsed = GAME_TIME - self.timer
            cycle = 20 - (elapsed // 450)
            self.color_timer = max(12, min(20, cycle))

    def _spawn_guest(self) -> None:
        occupied = {g.seat for g in self.guests}
        empty = [s for s in range(3) if s not in occupied]
        if empty:
            seat = self.rng.choice(empty)
            self.guests.append(Guest(seat, self.rng.randrange(4), PATIENCE_MAX))

    def _update_spawn(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_guest()
            elapsed = GAME_TIME - self.timer
            interval = 90 - (elapsed // 60)
            self.spawn_timer = max(40, min(90, interval))

    def _update_guests(self) -> None:
        for guest in list(self.guests):
            guest.patience -= 1
            if guest.patience <= 0:
                self.guests.remove(guest)
                self.heat += 5.0
                self.combo = 0
                self._burst(SEAT_X[guest.seat], SEAT_Y, GRAY, 4, 1.0, -1.0, 1.0, 15)
                self._check_game_over()

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
            return
        if self.super_timer <= 0:
            self.heat = max(0.0, self.heat - DECAY)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _check_game_over(self) -> None:
        if self.heat >= MAX_HEAT or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)

    # ------------------------------------------------------------------ #
    # Particle helpers                                                    #
    # ------------------------------------------------------------------ #

    def _burst(
        self,
        x: float,
        y: float,
        color: int,
        count: int,
        vxr: float,
        vy0: float,
        vy1: float,
        life: int,
    ) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x,
                    y,
                    self.rng.uniform(-vxr, vxr),
                    self.rng.uniform(vy0, vy1),
                    life,
                    color,
                )
            )

    def _spawn_match_particles(self, seat: int, super_active: bool) -> None:
        x, y = SEAT_X[seat], SEAT_Y
        if super_active:
            for _ in range(20):
                self.particles.append(
                    Particle(
                        float(x),
                        float(y),
                        self.rng.uniform(-2.0, 2.0),
                        self.rng.uniform(-3.0, -1.0),
                        self.rng.randint(25, 40),
                        TEA_COLORS[self.rng.randrange(4)],
                    )
                )
        else:
            for _ in range(8):
                self.particles.append(
                    Particle(
                        float(x),
                        float(y),
                        self.rng.uniform(-1.0, 1.0),
                        self.rng.uniform(-2.0, -0.5),
                        self.rng.randint(20, 30),
                        self.rng.choice((GREEN, WHITE)),
                    )
                )

    # ------------------------------------------------------------------ #
    # Input / update                                                      #
    # ------------------------------------------------------------------ #

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self.timer -= 1
        self._update_steep()
        self._update_brew_color()
        self._update_spawn()
        self._update_guests()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()
        if self.super_timer > 0:
            self.super_timer -= 1
        if self.shake_frames > 0:
            self.shake_frames -= 1
        self._check_game_over()

        if pyxel.btnp(pyxel.KEY_1):
            self.serve(0)
        elif pyxel.btnp(pyxel.KEY_2):
            self.serve(1)
        elif pyxel.btnp(pyxel.KEY_3):
            self.serve(2)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            seat = self._seat_at(pyxel.mouse_x, pyxel.mouse_y)
            if seat is not None:
                self.serve(seat)

    def _seat_at(self, x: int, y: int) -> int | None:
        for seat in range(3):
            if abs(x - SEAT_X[seat]) <= 24 and abs(y - SEAT_Y) <= 24:
                return seat
        return None

    # ------------------------------------------------------------------ #
    # Drawing                                                             #
    # ------------------------------------------------------------------ #

    def draw(self) -> None:
        ox = oy = 0
        if self.shake_frames > 0:
            ox = self.rng.randint(-2, 2)
            oy = self.rng.randint(-2, 2)

        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game(ox, oy)
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _center(self, s: str) -> int:
        return (WIDTH - len(s) * 4) // 2

    def _draw_title(self) -> None:
        pyxel.text(self._center("TEA CHAIN"), 60, "TEA CHAIN", LIME)
        pyxel.text(self._center("Tea Ceremony Chain"), 84, "Tea Ceremony Chain", WHITE)
        pyxel.text(self._center("Click or press 1-3 to serve"), 112, "Click or press 1-3 to serve", WHITE)
        pyxel.text(self._center("Steep longer for up to 3x"), 126, "Steep longer for up to 3x", YELLOW)
        pyxel.text(self._center("Match colors, build combo -> SUPER"), 140, "Match colors, build combo -> SUPER", CYAN)
        pyxel.text(self._center("Don't over-steep!"), 154, "Don't over-steep!", RED)
        pyxel.text(self._center("Press ENTER"), 190, "Press ENTER", GREEN)

    def _draw_game(self, ox: int, oy: int) -> None:
        pyxel.cls(NAVY)
        pyxel.rect(0, HEIGHT - 30, WIDTH, 30, BROWN)

        for guest in self.guests:
            self._draw_guest(guest, ox, oy)
        self._draw_master(ox, oy)
        self._draw_steep_meter(ox, oy)
        self._draw_hud()
        if self.super_timer > 0:
            self._draw_super_border()

        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color)
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) + ox, int(ft.y) + oy, ft.text, ft.color)

    def _draw_guest(self, guest: Guest, ox: int, oy: int) -> None:
        x, y = SEAT_X[guest.seat] + ox, SEAT_Y + oy
        col = TEA_COLORS[guest.color]

        pyxel.circ(x, y + 8, 7, WHITE)
        pyxel.rect(x - 7, y + 15, 14, 14, WHITE)

        pyxel.circ(x + 8, y - 24, 3, WHITE)
        pyxel.circ(x + 14, y - 30, 5, WHITE)
        pyxel.circ(x + 26, y - 36, 11, col)
        label = TEA_ABBR[guest.color]
        pyxel.text(x + 26 - len(label) * 2, y - 38, label, BLACK if guest.color == 3 else WHITE)
        pyxel.text(x - 10, y - 50, TEA_NAMES[guest.color], WHITE)

        ratio = guest.patience / PATIENCE_MAX
        barcol = GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        pyxel.rect(x - 15, y + 30, 30, 4, GRAY)
        pyxel.rect(x - 15, y + 30, int(30 * ratio), 4, barcol)

    def _draw_master(self, ox: int, oy: int) -> None:
        mx, my = MASTER_X + ox, 60 + oy
        pyxel.circ(mx, my, 8, WHITE)
        pyxel.rect(mx - 9, my + 8, 18, 20, WHITE)
        pyxel.circ(mx, my + 40, 11, TEA_COLORS[self.brew_color])
        name = TEA_NAMES[self.brew_color]
        pyxel.text(mx - len(name) * 2, my + 56, name, WHITE)

    def _draw_steep_meter(self, ox: int, oy: int) -> None:
        sx, sy = 20 + ox, 210 + oy
        sw, sh = 120, 10
        pyxel.rect(sx, sy, sw, sh, GRAY)
        ratio = self.steep / STEEP_MAX
        col = GREEN if ratio < 0.5 else (YELLOW if ratio < 0.8 else RED)
        pyxel.rect(sx, sy, int(sw * ratio), sh, col)
        pyxel.text(sx, sy - 8, "STEEP", WHITE)

    def _draw_hud(self) -> None:
        pyxel.text(5, 4, f"SCORE {self.score}", WHITE)
        if self.combo > 1:
            pyxel.text(5, 14, f"COMBO x{self.combo}", YELLOW)

        pyxel.text(120, 2, "TIME", LIGHT_BLUE)
        pyxel.rect(150, 4, 150, 5, GRAY)
        pyxel.rect(150, 4, int(150 * max(0, self.timer) / GAME_TIME), 5, LIGHT_BLUE)

        pyxel.text(120, 12, "HEAT", WHITE)
        pyxel.rect(150, 14, 150, 5, GRAY)
        hr = min(1.0, self.heat / MAX_HEAT)
        hcol = GREEN if hr < 0.5 else (YELLOW if hr < 0.8 else RED)
        pyxel.rect(150, 14, int(150 * hr), 5, hcol)

    def _draw_super_border(self) -> None:
        bc = TEA_COLORS[(pyxel.frame_count // 4) % 4]
        pyxel.rectb(0, 0, WIDTH, HEIGHT, bc)
        pyxel.rectb(1, 1, WIDTH - 2, HEIGHT - 2, bc)

    def _draw_game_over(self) -> None:
        pyxel.text(self._center("GAME OVER"), 70, "GAME OVER", RED)
        pyxel.text(self._center(f"SCORE {self.score}"), 100, f"SCORE {self.score}", WHITE)
        pyxel.text(self._center(f"BEST {self.best_score}"), 116, f"BEST {self.best_score}", YELLOW)
        pyxel.text(self._center(f"MAX COMBO {self.max_combo}"), 132, f"MAX COMBO {self.max_combo}", CYAN)
        pyxel.text(self._center("Press ENTER"), 180, "Press ENTER", GREEN)


if __name__ == "__main__":
    Game()
