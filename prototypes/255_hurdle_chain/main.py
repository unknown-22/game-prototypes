from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 190
HURDLE_WIDTH = 24
HURDLE_HEIGHT = 4
HURDLE_Y = GROUND_Y - HURDLE_HEIGHT - 10
PLAYER_RADIUS = 10
JUMP_VY = -7.0
GRAVITY = 0.45
COLOR_VALS: tuple[int, ...] = (8, 11, 5, 10)
COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
COLOR_CYCLE_FRAMES = 20
SUPER_DURATION = 300
HEAT_MISMATCH = 15.0
HEAT_CRASH = 25.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0
COMBO_THRESHOLD = 4
SPAWN_INTERVAL_START = 90
SPAWN_INTERVAL_END = 35
HURDLE_GAP_MIN = 80
HURDLE_GAP_MAX = 140
SCROLL_START = 1.5
SCROLL_END = 4.0
STUN_MISMATCH = 15
STUN_CRASH = 20
FPS = 30
TIMER_MAX = 1800

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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Hurdle:
    x: float
    y: float
    color: int
    cleared: bool = False
    scored: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    COLORS: ClassVar[tuple[int, ...]] = COLOR_VALS

    def __new__(cls, headless: bool = False) -> Game:
        obj = object.__new__(cls)
        obj._set_defaults()
        obj._headless = headless
        return obj

    def _set_defaults(self) -> None:
        self._headless: bool = False
        self.phase: Phase = Phase.TITLE
        self.player_y: float = float(GROUND_Y)
        self.player_vy: float = 0.0
        self.player_color_idx: int = 0
        self.player_color_timer: int = 0
        self.player_on_ground: bool = True
        self.player_stun: int = 0
        self.hurdles: list[Hurdle] = []
        self.hurdle_spawn_timer: int = 0
        self.scroll_speed: float = SCROLL_START
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.best_score: int = 0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.heat: float = 0.0
        self.timer_frames: int = TIMER_MAX
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trail: list[tuple[float, float]] = []
        self.best_trail: list[tuple[float, float]] = []
        self.rng: random.Random = random.Random()
        self.last_hurdle_x: float = float(SCREEN_W)
        self.play_time: int = 0

    def __init__(self, headless: bool = False) -> None:
        if not headless:
            pyxel.init(SCREEN_W, SCREEN_H, title="HURDLE CHAIN", fps=FPS)
            pyxel.run(self._update, self._draw)

    def _reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_y = float(GROUND_Y)
        self.player_vy = 0.0
        self.player_color_idx = 0
        self.player_color_timer = 0
        self.player_on_ground = True
        self.player_stun = 0
        self.hurdles.clear()
        self.hurdle_spawn_timer = 0
        self.scroll_speed = SCROLL_START
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_timer = 0
        self.super_mode = False
        self.heat = 0.0
        self.timer_frames = TIMER_MAX
        self.particles.clear()
        self.floating_texts.clear()
        self.ghost_trail.clear()
        self.last_hurdle_x = float(SCREEN_W)
        self.play_time = 0

    def _start_playing(self) -> None:
        self._reset()
        self.phase = Phase.PLAYING

    def _get_input(self) -> dict:
        if self._headless:
            return {"space": False, "space_p": False}
        return {
            "space": pyxel.btn(pyxel.KEY_SPACE),
            "space_p": pyxel.btnp(pyxel.KEY_SPACE),
        }

    def _player_color(self) -> int:
        return COLOR_VALS[self.player_color_idx]

    def _player_color_name(self) -> str:
        return COLOR_NAMES[self.player_color_idx]

    def _is_super(self) -> bool:
        return self.super_mode

    def _jump(self) -> None:
        if self.player_on_ground and self.player_stun <= 0:
            self.player_vy = JUMP_VY
            self.player_on_ground = False

    def _update_player(self) -> None:
        if self.player_stun > 0:
            self.player_stun -= 1
            if self.player_vy < 0:
                self.player_vy = 0.0
        self.player_vy += GRAVITY
        self.player_y += self.player_vy
        if self.player_y >= GROUND_Y:
            self.player_y = float(GROUND_Y)
            self.player_vy = 0.0
            self.player_on_ground = True

    def _update_color_cycle(self) -> None:
        self.player_color_timer += 1
        if self.player_color_timer >= COLOR_CYCLE_FRAMES:
            self.player_color_timer = 0
            self.player_color_idx = (self.player_color_idx + 1) % len(COLOR_VALS)

    def _spawn_hurdle(self) -> None:
        x = self.last_hurdle_x + self.rng.randint(HURDLE_GAP_MIN, HURDLE_GAP_MAX)
        color = self.rng.choice(COLOR_VALS)
        self.hurdles.append(Hurdle(x=float(x), y=float(HURDLE_Y), color=color))
        self.last_hurdle_x = x

    def _update_hurdles(self) -> None:
        self.hurdle_spawn_timer += 1
        spawn_interval = int(
            SPAWN_INTERVAL_START
            + (SPAWN_INTERVAL_END - SPAWN_INTERVAL_START)
            * (self.play_time / TIMER_MAX)
        )
        if self.hurdle_spawn_timer >= spawn_interval:
            self.hurdle_spawn_timer = 0
            self._spawn_hurdle()
        for h in self.hurdles:
            h.x -= self.scroll_speed
        self.hurdles = [h for h in self.hurdles if h.x > -HURDLE_WIDTH * 2]

    def _check_hurdle_clear(self) -> None:
        player_x = SCREEN_W // 4
        for h in self.hurdles:
            if h.scored:
                continue
            center_x = h.x + HURDLE_WIDTH / 2
            if abs(center_x - player_x) < self.scroll_speed * 2:
                h.scored = True
                is_airborne = self.player_y < HURDLE_Y
                if not is_airborne:
                    self.heat = min(HEAT_MAX, self.heat + HEAT_CRASH)
                    self.player_stun = STUN_CRASH
                    self.combo = 0
                    self._spawn_particles(player_x, self.player_y, 8, RED)
                    self._spawn_floating_text(player_x, GROUND_Y - 20, "CRASH!", RED)
                    return
                if self._is_super() or self._player_color() == h.color:
                    h.cleared = True
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    multiplier = 3 if self._is_super() else 1
                    points = int(10 * self.combo * multiplier)
                    self.score += points
                    self._spawn_particles(player_x, GROUND_Y, 6, h.color)
                    self._spawn_floating_text(player_x, GROUND_Y - 20, f"+{points}", LIME)
                    if self.combo >= 3:
                        self._spawn_floating_text(
                            player_x, GROUND_Y - 32, f"COMBO x{self.combo}", YELLOW
                        )
                else:
                    self.combo = 0
                    self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
                    self.player_stun = STUN_MISMATCH
                    self._spawn_particles(player_x, GROUND_Y, 5, GRAY)
                    self._spawn_floating_text(player_x, GROUND_Y - 20, "WRONG!", RED)
                self._check_super_activation()

    def _check_super_activation(self) -> None:
        if self.combo >= COMBO_THRESHOLD and not self._is_super():
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self._spawn_floating_text(
                SCREEN_W // 2, SCREEN_H // 2 - 20, "SUPER SPRINT!", YELLOW
            )
            self._spawn_particles(SCREEN_W // 2, GROUND_Y, 20, -1)

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0
                self._spawn_floating_text(
                    SCREEN_W // 2, SCREEN_H // 2 - 20, "SUPER END", GRAY
                )
            else:
                self._auto_jump()

    def _auto_jump(self) -> None:
        player_x = SCREEN_W // 4
        for h in self.hurdles:
            if h.scored:
                continue
            if h.x + HURDLE_WIDTH > player_x and h.x < player_x + PLAYER_RADIUS * 3:
                dist = h.x - player_x
                if 0 < dist < 50 and self.player_on_ground:
                    self._jump()
                    return

    def _update_heat(self) -> None:
        if self._is_super():
            return
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            self._spawn_floating_text(
                SCREEN_W // 2, SCREEN_H // 2, "GAME OVER", RED
            )
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timer(self) -> None:
        self.timer_frames -= 1
        if self.timer_frames <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
                self.best_trail = self.ghost_trail.copy()

    def _update_scroll_speed(self) -> None:
        t = self.play_time / TIMER_MAX
        self.scroll_speed = SCROLL_START + (SCROLL_END - SCROLL_START) * t

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            if color == -1:
                pcolor = self.rng.choice(COLOR_VALS)
            else:
                pcolor = color
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-2.5, -0.5)
            life = self.rng.randint(15, 25)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, color=pcolor, life=life)
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        life = 30
        if "SUPER" in text:
            life = 45
        elif "WRONG" in text or "CRASH" in text:
            life = 25
        elif "GAME OVER" in text:
            life = 60
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=life)
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

    def _record_ghost(self) -> None:
        if self.play_time % 5 == 0:
            self.ghost_trail.append((float(SCREEN_W // 4), self.player_y))

    def _update(self) -> None:
        inp = self._get_input()

        if self.phase == Phase.TITLE:
            self._update_title(inp)
        elif self.phase == Phase.PLAYING:
            self._update_playing(inp)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(inp)

        self._update_particles()
        self._update_floating_texts()

    def _update_title(self, inp: dict) -> None:
        if inp["space_p"]:
            self._start_playing()

    def _update_playing(self, inp: dict) -> None:
        self.play_time += 1
        self._update_scroll_speed()
        self._update_player()
        self._update_color_cycle()
        if self._is_super():
            self._update_super()
        else:
            self._update_heat()
        self._update_timer()
        self._update_hurdles()
        if inp["space_p"] and self.player_stun <= 0 and not self._is_super():
            self._jump()
        self._check_hurdle_clear()
        self._record_ghost()

    def _update_game_over(self, inp: dict) -> None:
        if inp["space_p"]:
            self.phase = Phase.TITLE
            self._reset()

    def _draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    def _draw_sky(self) -> None:
        for i in range(GROUND_Y):
            t = i / GROUND_Y
            if t < 0.3:
                col = NAVY
            elif t < 0.6:
                col = DARK_BLUE
            elif t < 0.85:
                col = LIGHT_BLUE
            else:
                col = WHITE
            pyxel.line(0, i, SCREEN_W, i, col)

    def _draw_track(self) -> None:
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, WHITE)
        offset = int(pyxel.frame_count * self.scroll_speed // 3) % 20
        px = -offset
        while px < SCREEN_W:
            pyxel.line(max(0, px), GROUND_Y + 2, min(SCREEN_W, px + 8), GROUND_Y + 2, WHITE)
            pyxel.line(max(0, px), GROUND_Y + 6, min(SCREEN_W, px + 10), GROUND_Y + 6, WHITE)
            px += 20

    def _draw_player(self) -> None:
        px = SCREEN_W // 4
        py = int(self.player_y)
        if self.player_stun > 0 and self.player_stun % 4 < 2:
            return
        if self._is_super():
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            color = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            pyxel.circb(px, py - 2, PLAYER_RADIUS + 2, color)
            pyxel.circb(px, py - 2, PLAYER_RADIUS + 4, color)
        color = self._player_color()
        pyxel.circ(px, py - PLAYER_RADIUS, PLAYER_RADIUS, color)
        pyxel.line(px - 2, py - PLAYER_RADIUS, px, py - PLAYER_RADIUS - 4, PEACH)
        pyxel.line(px + 2, py - PLAYER_RADIUS, px, py - PLAYER_RADIUS - 4, PEACH)
        pyxel.line(px, py - PLAYER_RADIUS, px - 4, py, PEACH)
        pyxel.line(px, py - PLAYER_RADIUS, px + 4, py, PEACH)
        pyxel.line(px, py, px - 3, py + 8, PEACH)
        pyxel.line(px, py, px + 3, py + 8, PEACH)
        if self.player_on_ground and self.player_stun <= 0:
            eye_h = py - PLAYER_RADIUS + 2
            pyxel.pset(px - 3, eye_h, BLACK)
            pyxel.pset(px + 3, eye_h, BLACK)

    def _draw_hurdle(self, h: Hurdle) -> None:
        hx = int(h.x)
        hy = int(h.y)
        color = h.color
        if h.cleared:
            color = GRAY
        pyxel.rect(hx, hy, HURDLE_WIDTH, HURDLE_HEIGHT, color)
        pyxel.rect(hx + 2, hy + HURDLE_HEIGHT, 2, GROUND_Y - hy - HURDLE_HEIGHT, GRAY)
        pyxel.rect(hx + HURDLE_WIDTH - 4, hy + HURDLE_HEIGHT, 2, GROUND_Y - hy - HURDLE_HEIGHT, GRAY)

    def _draw_ghost_trail(self) -> None:
        for tx, ty in self.ghost_trail:
            pyxel.circ(int(tx), int(ty), 1, CYAN)

    def _draw_best_trail(self) -> None:
        for tx, ty in self.best_trail:
            pyxel.circ(int(tx), int(ty), 1, ORANGE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 20, 4, f"COMBO: {self.combo}", YELLOW if self.combo >= 3 else WHITE)
        secs = max(0, self.timer_frames // FPS)
        timer_color = WHITE
        if secs <= 10:
            timer_color = RED
        elif secs <= 20:
            timer_color = ORANGE
        pyxel.text(SCREEN_W - 50, 4, f"TIME: {secs}s", timer_color)

        color = self._player_color()
        color_name = self._player_color_name()
        pyxel.text(4, 16, f"COLOR: {color_name}", color)
        pyxel.circ(60, 22, 4, color)

        heat_w = 60
        heat_h = 5
        pyxel.rectb(4, GROUND_Y + 4, heat_w, heat_h, WHITE)
        heat_fill = int(heat_w * self.heat / HEAT_MAX)
        heat_color = LIME
        if self.heat > 60:
            heat_color = ORANGE
        if self.heat > 80:
            heat_color = RED
        pyxel.rect(4, GROUND_Y + 4, heat_fill, heat_h, heat_color)

        if self._is_super():
            super_secs = self.super_timer // FPS + 1
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            rcolor = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            pyxel.text(SCREEN_W // 2 - 30, 20, f"SUPER! {super_secs}s", rcolor)

        if self.player_stun > 0:
            pyxel.text(SCREEN_W // 2 - 20, 34, "STUN!", RED)

    def _draw_title(self) -> None:
        self._draw_sky()
        self._draw_track()
        pyxel.text(SCREEN_W // 2 - 40, 60, "HURDLE CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 48, 80, "Auto-run hurdle race!", LIME)
        pyxel.text(SCREEN_W // 2 - 55, 100, "SPACE: Jump over hurdles", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 112, "Player color cycles every 0.7s", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 124, "Match color = COMBO + Score", LIME)
        pyxel.text(SCREEN_W // 2 - 55, 136, "Wrong color = COMBO reset + HEAT", RED)
        pyxel.text(SCREEN_W // 2 - 55, 148, "Hit hurdle = HEAT + Stun", RED)
        pyxel.text(SCREEN_W // 2 - 55, 160, "COMBO x4 = SUPER SPRINT!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 55, 172, "SUPER: 3x score, auto-jump, 10s", YELLOW)
        pyxel.text(SCREEN_W // 2 - 55, 184, "HEAT 100 = GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 55, 196, "60s to score as high as you can!", WHITE)
        pyxel.text(SCREEN_W // 2 - 45, 215, "SPACE to start", CYAN)
        if self.best_score > 0:
            pyxel.text(
                SCREEN_W // 2 - 30, 228, f"BEST: {self.best_score}", YELLOW
            )

    def _draw_playing(self) -> None:
        self._draw_sky()
        self._draw_track()
        self._draw_ghost_trail()
        self._draw_best_trail()
        for h in self.hurdles:
            self._draw_hurdle(h)
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 40, 140, 70, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 40, 140, 70, RED)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 32, "GAME OVER", RED)
        pyxel.text(
            SCREEN_W // 2 - 35, SCREEN_H // 2 - 16,
            f"SCORE: {self.score}",
            WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 40, SCREEN_H // 2 - 4,
            f"MAX COMBO: {self.max_combo}",
            YELLOW,
        )
        if self.score >= self.best_score and self.score > 0:
            pyxel.text(
                SCREEN_W // 2 - 25, SCREEN_H // 2 + 8,
                "NEW BEST!",
                YELLOW,
            )
        pyxel.text(
            SCREEN_W // 2 - 45, SCREEN_H // 2 + 22,
            "SPACE to retry",
            CYAN,
        )


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
