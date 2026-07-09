from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240

HAND_X = 160
HAND_Y = 40
STRING_END = 180
GRAVITY = 0.3
BOUNCE_FACTOR = -0.6
CATCH_WINDOW = 30

COLOR_CYCLE_FRAMES = 90
SUPER_COMBO_THRESHOLD = 4
SUPER_DURATION = 300
SUPER_SCORE_MULT = 3

HEAT_WRONG_CATCH = 15
HEAT_MISS = 5
HEAT_DECAY = 0.05
HEAT_MAX = 100
HEAT_SHAKE_THRESHOLD = 60

GAME_DURATION = 60.0

# Pyxel color indices
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

YO_COLORS: list[tuple[int, str]] = [
    (RED, "RED"),
    (LIME, "GREEN"),
    (DARK_BLUE, "DARK_BLUE"),
    (YELLOW, "YELLOW"),
]

RAINBOW_COLORS: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]


# --- Data Classes ---
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
    vy: float = -1.0


@dataclass
class Yoyo:
    x: float
    y: float
    vy: float
    color_idx: int
    on_string: bool
    returning: bool


# --- Game Class ---
class Game:
    phase: Phase
    yoyo: Yoyo
    score: int
    combo: int
    max_combo: int
    super_mode: bool
    super_timer: int
    heat: float
    timer_frames: float
    particles: list[Particle]
    floating_texts: list[FloatingText]
    _rng: random.Random
    _color_timer: int
    _last_caught_color: int | None
    _passed_hand: bool

    def __new__(cls) -> Game:
        instance: Game = super().__new__(cls)
        instance.phase = Phase.TITLE
        instance.yoyo = Yoyo(
            x=float(HAND_X), y=float(HAND_Y), vy=0.0, color_idx=0,
            on_string=True, returning=False,
        )
        instance.score = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.super_mode = False
        instance.super_timer = 0
        instance.heat = 0.0
        instance.timer_frames = GAME_DURATION * 60.0
        instance.particles = []
        instance.floating_texts = []
        instance._rng = random.Random()
        instance._color_timer = 0
        instance._last_caught_color = None
        instance._passed_hand = False
        return instance

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="YOYO CHAIN", fps=60)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.yoyo = Yoyo(
            x=float(HAND_X), y=float(HAND_Y), vy=0.0, color_idx=0,
            on_string=True, returning=False,
        )
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.timer_frames = GAME_DURATION * 60.0
        self.particles.clear()
        self.floating_texts.clear()
        self._color_timer = 0
        self._last_caught_color = None
        self._passed_hand = False

    # --- Public update/draw entry points ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_playing()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self._start_playing()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # --- State transitions ---
    def _start_playing(self) -> None:
        self.phase = Phase.PLAYING
        self.yoyo = Yoyo(
            x=float(HAND_X), y=float(HAND_Y), vy=0.0,
            color_idx=self._rng.randrange(len(YO_COLORS)),
            on_string=True, returning=False,
        )
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.timer_frames = GAME_DURATION * 60.0
        self.particles.clear()
        self.floating_texts.clear()
        self._color_timer = 0
        self._last_caught_color = None
        self._passed_hand = False

    # --- PLAYING update ---
    def _update_playing(self) -> None:
        self.timer_frames -= 1
        self._update_color_cycle()
        self._update_super_mode()
        self._update_yoyo_physics()
        self._update_particles()
        self._update_floating_texts()
        # Check game-over BEFORE heat decays (pitfall: decay-before-check)
        if self.timer_frames <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        self._update_heat_decay()

    def _update_color_cycle(self) -> None:
        self._color_timer += 1
        if self._color_timer >= COLOR_CYCLE_FRAMES:
            self._color_timer = 0
            self.yoyo.color_idx = (self.yoyo.color_idx + 1) % len(YO_COLORS)

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0
            self.combo = 0
            return
        if self._rng.random() < 0.4:
            col = self._rng.choice(RAINBOW_COLORS)
            self.particles.append(Particle(
                x=self.yoyo.x + self._rng.uniform(-5, 5),
                y=self.yoyo.y + self._rng.uniform(-5, 5),
                vx=self._rng.uniform(-0.5, 0.5),
                vy=self._rng.uniform(-0.5, 0.5),
                life=12,
                color=col,
                size=1,
            ))

    def _update_yoyo_physics(self) -> None:
        y = self.yoyo
        y.vy += GRAVITY

        if y.on_string:
            y.y += y.vy
            if y.y >= STRING_END:
                y.y = float(STRING_END)
                y.vy *= BOUNCE_FACTOR
                y.returning = True
            if y.returning and y.y <= HAND_Y + CATCH_WINDOW:
                self._try_catch()
            if y.y <= HAND_Y and y.returning:
                self._on_miss()
        else:
            y.y += y.vy
            if y.y <= -10:
                y.y = float(HAND_Y)
                y.vy = 0.0
                y.on_string = True
                y.returning = False

    def _try_catch(self) -> None:
        if self.super_mode:
            self._execute_catch(same_color=True)
        elif pyxel.btnp(pyxel.KEY_SPACE):
            same = self._check_same_color()
            self._execute_catch(same_color=same)

    def _check_same_color(self) -> bool:
        yoyo_color = YO_COLORS[self.yoyo.color_idx][0]
        return self._last_caught_color is None or yoyo_color == self._last_caught_color

    def _execute_catch(self, *, same_color: bool) -> None:
        yoyo_color = YO_COLORS[self.yoyo.color_idx][0]

        if same_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            base_score = 10
            mult = 1.0 + self.combo * 0.5
            if self.super_mode:
                mult *= SUPER_SCORE_MULT
            points = int(base_score * mult)
            self.score += points
            self._spawn_catch_particles(self.yoyo.color_idx)
            self.floating_texts.append(FloatingText(
                x=self.yoyo.x, y=self.yoyo.y,
                text=f"+{points}", life=30, color=yoyo_color,
            ))
            if not self.super_mode and self.combo >= SUPER_COMBO_THRESHOLD:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self.floating_texts.append(FloatingText(
                    x=self.yoyo.x, y=self.yoyo.y - 12,
                    text="SUPER!", life=60, color=YELLOW,
                ))
        else:
            self.heat += HEAT_WRONG_CATCH
            self.combo = 0
            self._spawn_catch_particles(self.yoyo.color_idx)
            self.floating_texts.append(FloatingText(
                x=self.yoyo.x, y=self.yoyo.y,
                text="WRONG!", life=30, color=RED,
            ))

        self._last_caught_color = yoyo_color
        self.yoyo.y = float(HAND_Y)
        self.yoyo.vy = 0.0
        self.yoyo.on_string = True
        self.yoyo.returning = False

    def _on_miss(self) -> None:
        self.heat += HEAT_MISS
        self.combo = 0
        self.yoyo.on_string = False
        self.yoyo.vy = -3.0

    def _spawn_catch_particles(self, color_idx: int) -> None:
        count = 15 if self.super_mode else self._rng.randint(5, 8)
        yoyo_color = YO_COLORS[color_idx][0]
        for _ in range(count):
            col = self._rng.choice(RAINBOW_COLORS) if self.super_mode else yoyo_color
            self.particles.append(Particle(
                x=self.yoyo.x, y=self.yoyo.y,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.0, 2.0),
                life=self._rng.randint(10, 20),
                color=col,
            ))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_heat_decay(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # --- PLAYING draw ---
    def _draw_playing(self) -> None:
        ox, oy = self._shake_offset()

        # Ground line
        pyxel.line(0, 200 + oy, SCREEN_W, 200 + oy, GRAY)

        # String
        pyxel.line(
            HAND_X + ox, HAND_Y + oy,
            int(self.yoyo.x) + ox, int(self.yoyo.y) + oy,
            WHITE,
        )

        # Hand
        pyxel.rect(HAND_X - 5 + ox, HAND_Y - 5 + oy, 10, 10, PEACH)

        # Yoyo
        self._draw_yoyo(ox, oy)

        # Particles
        for p in self.particles:
            alpha = p.life / 20
            col = p.color if alpha > 0.3 else GRAY
            pyxel.circ(int(p.x) + ox, int(p.y) + oy, p.size, col)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 60
            col = ft.color if alpha > 0.3 else GRAY
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2 + ox, int(ft.y) + oy, ft.text, col)

        # HUD
        self._draw_hud()

    def _shake_offset(self) -> tuple[int, int]:
        if self.heat <= HEAT_SHAKE_THRESHOLD:
            return (0, 0)
        # Deterministic shake based on frame count
        phase_val = pyxel.frame_count
        ox = (phase_val // 3) % 5 - 2
        oy = (phase_val // 4) % 5 - 2
        return (ox, oy)

    def _draw_yoyo(self, ox: int, oy: int) -> None:
        cx = int(self.yoyo.x) + ox
        cy = int(self.yoyo.y) + oy
        if self.super_mode:
            col = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
        else:
            col = YO_COLORS[self.yoyo.color_idx][0]
        pyxel.circ(cx, cy, 10, col)
        pyxel.circb(cx, cy, 10, WHITE)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        combo_color = YELLOW if self.super_mode else WHITE
        pyxel.text(4, 14, f"COMBO: {self.combo}", combo_color)
        if self.super_mode:
            s_left = self.super_timer // 60 + 1
            pyxel.text(4, 24, f"SUPER {s_left}s", YELLOW)

        seconds_left = max(0.0, self.timer_frames / 60.0)
        timer_color = RED if seconds_left <= 10 else WHITE
        pyxel.text(SCREEN_W // 2 - 20, 4, f"TIME: {seconds_left:.1f}", timer_color)

        bar_x = SCREEN_W - 20
        bar_y = 10
        bar_w = 12
        bar_h = 80
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_h = int((self.heat / HEAT_MAX) * bar_h)
        heat_color = RED if self.heat > HEAT_SHAKE_THRESHOLD else ORANGE
        if heat_h > 0:
            pyxel.rect(bar_x + 1, bar_y + bar_h - heat_h, bar_w - 2, heat_h, heat_color)
        pyxel.text(bar_x - 2, bar_y - 8, "HEAT", GRAY)

    # --- TITLE draw ---
    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 60, "YOYO CHAIN", WHITE)
        # Decorative yoyo
        cx = SCREEN_W // 2
        bounce_y = 100 + int(pyxel.sin(pyxel.frame_count * 3) * 20)
        pyxel.line(cx, 80, cx, bounce_y, WHITE)
        color_i = (pyxel.frame_count // 90) % len(YO_COLORS)
        pyxel.circ(cx, bounce_y, 12, YO_COLORS[color_i][0])
        pyxel.circb(cx, bounce_y, 12, WHITE)

        if pyxel.frame_count % 40 < 20:
            pyxel.text(SCREEN_W // 2 - 48, 145, "PRESS SPACE", YELLOW)
        pyxel.text(SCREEN_W // 2 - 55, 170, "SPACE to catch", GRAY)
        pyxel.text(SCREEN_W // 2 - 70, 185, "Same color = COMBO", GRAY)
        pyxel.text(SCREEN_W // 2 - 50, 200, "COMBOx4 = SUPER", YELLOW)

    # --- GAME_OVER draw ---
    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, 70, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 50, 105, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 50, 120, f"MAX COMBO: {self.max_combo}", WHITE)
        msg = "HEAT OVERLOAD!" if self.heat >= HEAT_MAX else "TIME UP!"
        pyxel.text(SCREEN_W // 2 - len(msg) * 2, 140, msg, ORANGE)
        if pyxel.frame_count % 40 < 20:
            pyxel.text(SCREEN_W // 2 - 65, 175, "PRESS SPACE to retry", YELLOW)


# --- Entry point ---
if __name__ == "__main__":
    Game()
