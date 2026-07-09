from __future__ import annotations

import math
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
INFO_H = 20
FLOOR_Y = 220
PLAY_AREA_TOP = 24
PLAY_AREA_BOTTOM = 216
GRAVITY = 0.3
MAX_FALL_SPEED = 8.0
SWING_DAMPING = 0.995
RELEASE_SPEED_BOOST = 1.05
GRAB_RADIUS = 40
SUPER_GRAB_RADIUS = 60
SUPER_DURATION = 300
SUPER_SCORE_MULT = 3
HEAT_PER_SWING = 3.0
HEAT_PER_SUPER_FRAME = 0.15
HEAT_DECAY = 0.02
HEAT_COOLDOWN = 0.1
MAX_HEAT = 100.0
VINE_COUNT = 8
VINE_SPAWN_INTERVAL = 90
SCORE_PER_SWING = 10
COMBO_BONUS = 5
SUPER_THRESHOLD = 5
MIN_VINE_DIST = 60

# Pyxel colors
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

VINE_COLORS = [RED, ORANGE, YELLOW, LIME]
RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]


# --- Data Classes ---
@dataclass
class Vine:
    x: float
    y: float
    length: float
    color: int
    grabbed: bool = False

    @property
    def anchor_x(self) -> float:
        return self.x

    @property
    def anchor_y(self) -> float:
        return self.y

    @property
    def grab_x(self) -> float:
        angle = 0.3
        return self.x + self.length * math.sin(angle)

    @property
    def grab_y(self) -> float:
        angle = 0.3
        return self.y + self.length * math.cos(angle)


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


# --- Game Class ---
class Game:
    phase: Phase
    score: int
    combo: int
    max_combo: int
    super_mode: bool
    super_timer: int
    heat: float
    vines: list[Vine]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    player_x: float
    player_y: float
    player_vx: float
    player_vy: float
    _rng: random.Random
    _swing_angle: float
    _swing_angular_vel: float
    _attached_vine: Vine | None
    _last_vine_color: int | None
    _vine_spawn_timer: int
    _on_ground: bool
    _was_clicked: bool
    _death_cause: str

    def __new__(cls) -> Game:
        instance: Game = super().__new__(cls)
        instance.phase = Phase.TITLE
        instance.score = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.super_mode = False
        instance.super_timer = 0
        instance.heat = 0.0
        instance.vines = []
        instance.particles = []
        instance.floating_texts = []
        instance.player_x = float(SCREEN_W // 2)
        instance.player_y = float(PLAY_AREA_TOP + 40)
        instance.player_vx = 0.0
        instance.player_vy = 0.0
        instance._rng = random.Random()
        instance._swing_angle = 0.0
        instance._swing_angular_vel = 0.0
        instance._attached_vine = None
        instance._last_vine_color = None
        instance._vine_spawn_timer = 0
        instance._on_ground = False
        instance._was_clicked = False
        instance._death_cause = ""
        return instance

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="VINE CHAIN", fps=60)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.vines.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.player_x = float(SCREEN_W // 2)
        self.player_y = float(PLAY_AREA_TOP + 40)
        self.player_vx = 0.0
        self.player_vy = 0.0
        self._swing_angle = 0.0
        self._swing_angular_vel = 0.0
        self._attached_vine = None
        self._last_vine_color = None
        self._vine_spawn_timer = 0
        self._on_ground = False
        self._was_clicked = False
        self._death_cause = ""

    # --- Public update/draw entry points ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_playing()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
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
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.vines.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.player_x = float(SCREEN_W // 2)
        self.player_y = float(PLAY_AREA_TOP + 40)
        self.player_vx = 0.0
        self.player_vy = 0.0
        self._swing_angle = 0.0
        self._swing_angular_vel = 0.0
        self._attached_vine = None
        self._last_vine_color = None
        self._vine_spawn_timer = 0
        self._on_ground = False
        self._was_clicked = False
        self._death_cause = ""
        self._spawn_initial_vines()

    # --- PLAYING update ---
    def _update_playing(self) -> None:
        self._handle_input()
        self._update_super_mode()
        self._update_physics()
        self._update_heat()
        self._update_vines()
        self._update_particles()
        self._update_floating_texts()
        self._check_game_over()

    def _handle_input(self) -> None:
        clicked = pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        if self.super_mode:
            self._super_auto_grab()
            return
        if not clicked:
            return
        if self._attached_vine is not None:
            self._release_vine()
        else:
            self._try_grab_vine()

    def _try_grab_vine(self) -> None:
        best: Vine | None = None
        best_dist = float("inf")
        for v in self.vines:
            if v.grabbed:
                continue
            dx = self.player_x - v.x
            dy = self.player_y - (v.y + v.length)
            dist = math.hypot(dx, dy)
            if dist < GRAB_RADIUS and dist < best_dist:
                best = v
                best_dist = dist
        if best is not None:
            self._grab_vine(best)

    def _super_auto_grab(self) -> None:
        best: Vine | None = None
        best_dist = float("inf")
        for v in self.vines:
            if v.grabbed:
                continue
            dx = self.player_x - v.x
            dy = self.player_y - (v.y + v.length)
            dist = math.hypot(dx, dy)
            if dist < SUPER_GRAB_RADIUS and dist < best_dist:
                best = v
                best_dist = dist
        if best is not None:
            self._grab_vine(best)

    def _grab_vine(self, vine: Vine) -> None:
        if self._attached_vine is not None:
            self._attached_vine.grabbed = False
        vine.grabbed = True
        self._attached_vine = vine
        dx = self.player_x - vine.x
        dy = self.player_y - vine.y
        self._swing_angle = math.atan2(dx, dy)
        speed = math.hypot(self.player_vx, self.player_vy)
        direction = 1.0 if self.player_vx >= 0 else -1.0
        self._swing_angular_vel = direction * speed / vine.length * 0.5

        color_ok = self._last_vine_color is None or vine.color == self._last_vine_color
        if color_ok or self.super_mode:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
        else:
            self.combo = 0

        self._last_vine_color = vine.color

        if not self.super_mode and self.combo >= SUPER_THRESHOLD:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self.floating_texts.append(FloatingText(
                x=self.player_x, y=self.player_y - 16,
                text="SUPER SWING!", life=60, color=YELLOW,
            ))

        burst_count = 12 if self.super_mode else 6
        for _ in range(burst_count):
            col = self._rng.choice(RAINBOW_COLORS) if self.super_mode else vine.color
            self.particles.append(Particle(
                x=self.player_x, y=self.player_y,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-1.5, 1.5),
                life=self._rng.randint(10, 20),
                color=col,
            ))

    def _release_vine(self) -> None:
        if self._attached_vine is None:
            return
        self._attached_vine.grabbed = False
        self._attached_vine = None

        base = SCORE_PER_SWING + COMBO_BONUS * self.combo
        mult = SUPER_SCORE_MULT if self.super_mode else 1
        points = base * mult
        self.score += points

        self.floating_texts.append(FloatingText(
            x=self.player_x, y=self.player_y,
            text=f"+{points}", life=30, color=WHITE,
        ))

        for _ in range(8):
            col = self._rng.choice(RAINBOW_COLORS) if self.super_mode else WHITE
            self.particles.append(Particle(
                x=self.player_x, y=self.player_y,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.0, 2.0),
                life=self._rng.randint(8, 16),
                color=col,
            ))

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0
            self.combo = 0
            return
        if self._rng.random() < 0.5:
            col = self._rng.choice(RAINBOW_COLORS)
            self.particles.append(Particle(
                x=self.player_x + self._rng.uniform(-6, 6),
                y=self.player_y + self._rng.uniform(-6, 6),
                vx=self._rng.uniform(-0.8, 0.8),
                vy=self._rng.uniform(-1.5, 0.0),
                life=self._rng.randint(15, 30),
                color=col,
                size=1,
            ))

    def _update_physics(self) -> None:
        if self._attached_vine is not None:
            self._update_swing_physics()
        else:
            self._update_freefall_physics()
        self._wrap_player()

    def _update_swing_physics(self) -> None:
        vine = self._attached_vine
        assert vine is not None
        gravity_tangent = GRAVITY * math.sin(self._swing_angle)
        self._swing_angular_vel -= gravity_tangent
        self._swing_angular_vel *= SWING_DAMPING
        self._swing_angle += self._swing_angular_vel

        self.player_x = vine.x + vine.length * math.sin(self._swing_angle)
        self.player_y = vine.y + vine.length * math.cos(self._swing_angle)

        self.player_vx = vine.length * math.cos(self._swing_angle) * self._swing_angular_vel
        self.player_vy = -vine.length * math.sin(self._swing_angle) * self._swing_angular_vel

        self._on_ground = False

    def _update_freefall_physics(self) -> None:
        self.player_vy += GRAVITY
        if self.player_vy > MAX_FALL_SPEED:
            self.player_vy = MAX_FALL_SPEED
        self.player_x += self.player_vx
        self.player_y += self.player_vy

        if self.player_y >= FLOOR_Y:
            self.player_y = float(FLOOR_Y)
            self.player_vy = 0.0
            self.player_vx *= 0.9
            self._on_ground = True
        else:
            self._on_ground = False

        if self._attached_vine is None and not self._on_ground:
            trail_col = self._rng.choice(RAINBOW_COLORS) if self.super_mode else PEACH
            self.particles.append(Particle(
                x=self.player_x, y=self.player_y,
                vx=self._rng.uniform(-0.3, 0.3),
                vy=self._rng.uniform(-0.3, 0.3),
                life=8,
                color=trail_col,
                size=1,
            ))

    def _wrap_player(self) -> None:
        if self.player_x < -10:
            self.player_x = float(SCREEN_W + 10)
            if self._attached_vine is not None:
                self._attached_vine.grabbed = False
                self._attached_vine = None
        elif self.player_x > SCREEN_W + 10:
            self.player_x = -10.0
            if self._attached_vine is not None:
                self._attached_vine.grabbed = False
                self._attached_vine = None

    def _update_heat(self) -> None:
        if self.super_mode:
            self.heat += HEAT_PER_SUPER_FRAME
        elif self._on_ground:
            self.heat = max(0.0, self.heat - HEAT_DECAY)
        elif self._attached_vine is not None:
            self.heat = max(0.0, self.heat - HEAT_COOLDOWN)

        if self.heat > MAX_HEAT:
            self.heat = MAX_HEAT

    def _update_vines(self) -> None:
        scroll_speed = 1.5
        self._vine_spawn_timer -= 1
        for v in self.vines:
            v.x -= scroll_speed

        self.vines = [v for v in self.vines if v.x > -40]

        if self._vine_spawn_timer <= 0:
            self._vine_spawn_timer = VINE_SPAWN_INTERVAL + self._rng.randint(-20, 20)
            if len(self.vines) < VINE_COUNT:
                self._spawn_vine()

        if not self.vines:
            self._spawn_initial_vines()

    def _spawn_vine(self) -> None:
        spawn_x = float(SCREEN_W + self._rng.randint(10, 60))
        length = float(self._rng.randint(80, 180))
        color = self._rng.choice(VINE_COLORS)

        if self.vines:
            rightmost = max(v.x for v in self.vines)
            if spawn_x - rightmost < MIN_VINE_DIST:
                spawn_x = rightmost + MIN_VINE_DIST + self._rng.randint(0, 30)

        self.vines.append(Vine(x=spawn_x, y=float(PLAY_AREA_TOP), length=length, color=color))

    def _spawn_initial_vines(self) -> None:
        self.vines.clear()
        for i in range(VINE_COUNT):
            x = 40.0 + i * (SCREEN_W - 80) / (VINE_COUNT - 1)
            v = Vine(
                x=x,
                y=float(PLAY_AREA_TOP),
                length=float(self._rng.randint(80, 180)),
                color=self._rng.choice(VINE_COLORS),
            )
            self.vines.append(v)

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

    def _check_game_over(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self._death_cause = "Overheated!"
        elif self.player_y > SCREEN_H + 20:
            self.phase = Phase.GAME_OVER
            self._death_cause = "Fell!"

    # --- PLAYING draw ---
    def _draw_playing(self) -> None:
        self._draw_background()
        self._draw_vines()
        self._draw_particles()
        self._draw_player()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_super_border()

    def _draw_background(self) -> None:
        for i in range(6):
            y = PLAY_AREA_TOP + i * (FLOOR_Y - PLAY_AREA_TOP) // 6
            shade = NAVY if i % 2 == 0 else DARK_BLUE
            pyxel.rect(0, y, SCREEN_W, (FLOOR_Y - PLAY_AREA_TOP) // 6 + 1, shade)

        pyxel.rect(0, FLOOR_Y, SCREEN_W, SCREEN_H - FLOOR_Y, BROWN)
        pyxel.line(0, FLOOR_Y, SCREEN_W, FLOOR_Y, GREEN)

    def _draw_vines(self) -> None:
        for v in self.vines:
            line_color = YELLOW if v.grabbed else BROWN
            end_x = int(v.x)
            end_y = int(v.y + v.length)
            if v.grabbed:
                end_x = int(self.player_x)
                end_y = int(self.player_y)
            pyxel.line(int(v.x), int(v.y), end_x, end_y, line_color)
            pyxel.circb(int(v.x), int(v.y), 3, GREEN)
            if not v.grabbed:
                tip_x = int(v.x)
                tip_y = int(v.y + v.length)
                pyxel.circ(tip_x, tip_y, 4, v.color)
                pyxel.circb(tip_x, tip_y, 5, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            col = p.color if alpha > 0.3 else GRAY
            pyxel.circ(int(p.x), int(p.y), p.size, col)

    def _draw_player(self) -> None:
        if self.super_mode:
            col = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
        else:
            col = PEACH
        pyxel.circ(int(self.player_x), int(self.player_y), 8, col)
        pyxel.circb(int(self.player_x), int(self.player_y), 9, WHITE)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 60.0
            col = ft.color if alpha > 0.3 else GRAY
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, col)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, INFO_H, BLACK)
        pyxel.line(0, INFO_H, SCREEN_W, INFO_H, GRAY)

        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        combo_color = YELLOW if self.super_mode else WHITE
        pyxel.text(4, 12, f"COMBO: {self.combo}", combo_color)

        if self.super_mode:
            s_left = self.super_timer // 60 + 1
            pyxel.text(SCREEN_W // 2 - 20, 4, f"SUPER {s_left}s", YELLOW)

        bar_x = SCREEN_W - 24
        bar_y = 4
        bar_w = 16
        bar_h = INFO_H - 4
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_fill = int((self.heat / MAX_HEAT) * (bar_h - 4))
        if self.heat < MAX_HEAT * 0.33:
            heat_color = GREEN
        elif self.heat < MAX_HEAT * 0.66:
            heat_color = YELLOW
        elif self.heat < MAX_HEAT * 0.85:
            heat_color = RED
        else:
            heat_color = PINK
        if heat_fill > 0:
            pyxel.rect(bar_x + 2, bar_y + bar_h - 2 - heat_fill, bar_w - 4, heat_fill, heat_color)
        pyxel.text(bar_x - 6, bar_y - 1, "H", GRAY)

        pyxel.text(SCREEN_W // 2 - 52, SCREEN_H - 10, "CLICK TO GRAB/RELEASE", GRAY)

    def _draw_super_border(self) -> None:
        if not self.super_mode:
            return
        col = RAINBOW_COLORS[(pyxel.frame_count // 6) % len(RAINBOW_COLORS)]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, col)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, col)

    # --- TITLE draw ---
    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        self._draw_background()

        title_x = SCREEN_W // 2 - 42
        pyxel.text(title_x, 60, "VINE CHAIN", WHITE)

        vine_angles = [0.2 + i * 0.6 for i in range(3)]
        base_x = SCREEN_W // 2
        base_y = 90
        for i, angle in enumerate(vine_angles):
            vx = base_x + 60 * math.sin(angle)
            vy = base_y + 60 * math.cos(angle)
            color = VINE_COLORS[i % len(VINE_COLORS)]
            pyxel.line(base_x, base_y, int(vx), int(vy), BROWN)
            pyxel.circ(int(vx), int(vy), 5, color)
            pyxel.circb(int(vx), int(vy), 6, WHITE)

        player_angle = 0.2 + ((pyxel.frame_count // 2) % 100) / 100.0 * 0.6
        px = base_x + 60 * math.sin(player_angle)
        py = base_y + 60 * math.cos(player_angle)
        pyxel.circ(int(px), int(py), 8, PEACH)
        pyxel.circb(int(px), int(py), 9, WHITE)
        pyxel.line(base_x, base_y, int(px), int(py), YELLOW)

        if pyxel.frame_count % 40 < 20:
            pyxel.text(SCREEN_W // 2 - 40, 175, "CLICK TO START", YELLOW)

        pyxel.text(SCREEN_W // 2 - 72, 200, "Click to grab/release vines", GRAY)
        pyxel.text(SCREEN_W // 2 - 72, 212, "Same color = COMBO, 5x = SUPER!", GRAY)

    # --- GAME_OVER draw ---
    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(SCREEN_W // 2 - 30, 60, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 45, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 50, 105, f"MAX COMBO: {self.max_combo}", WHITE)
        pyxel.text(SCREEN_W // 2 - len(self._death_cause) * 2, 125, self._death_cause, ORANGE)
        if pyxel.frame_count % 40 < 20:
            pyxel.text(SCREEN_W // 2 - 70, 160, "CLICK or R to retry", YELLOW)


# --- Entry point ---
if __name__ == "__main__":
    Game()
