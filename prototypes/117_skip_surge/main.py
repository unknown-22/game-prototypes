from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    SCORING = auto()
    GAME_OVER = auto()


@dataclass
class Ripple:
    x: float
    y: float
    radius: float = 12.0
    color: int = 8
    active: bool = True
    vx: float = 0.0

    def update(self) -> None:
        self.x += self.vx
        if self.x < 10 or self.x > 310:
            self.vx = -self.vx
            self.x = max(10.0, min(310.0, self.x))


@dataclass
class Stone:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    bounces: int = 0
    combo_color: int = -1
    super_mode: bool = False
    super_timer: int = 0
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 1


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int = 7


SCREEN_W = 320
SCREEN_H = 240
WATER_Y = 180
WATER_H = 60
RIPPLE_COLORS: list[int] = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
STONE_GRAVITY = 0.15
THROW_ANGLE = math.radians(60)
POWER_MIN = 30.0
POWER_MAX = 100.0
POWER_CHARGE_SPEED = 0.8
BOUNCE_VY_FACTOR = 0.7
BOUNCE_VX_FACTOR = 0.95
SUPER_BOUNCE_VY_FACTOR = 0.85
SUPER_BOUNCE_VX_FACTOR = 0.98
SUPER_DURATION = 300  # 5 seconds at 60fps
COMBO_THRESHOLD = 4
HEAT_PER_WRONG = 2.0
HEAT_PER_MISS = 1.0
HEAT_DECAY = 1.0 / 60.0  # per frame
MAX_HEAT = 100.0
GAME_TIME = 90 * 60  # 90 seconds in frames
SCORING_DELAY = 90  # 1.5 seconds
MIN_RIPPLES = 8
MAX_RIPPLES = 12
RIPPLE_RESPAWN_MIN = 20
RIPPLE_RESPAWN_MAX = 50
RIPPLE_DRIFT_SPEED = 0.2


class Game:
    _COLOR_NAMES: ClassVar[dict[int, str]] = {8: "RED", 3: "GRN", 5: "BLU", 10: "YEL"}

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Skip Surge", fps=60)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.stone: Stone | None = None
        self.ripples: list[Ripple] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: int = GAME_TIME
        self.aim_power: float = POWER_MIN
        self.throw_count: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self._scoring_countdown: int = 0
        self._rainbow_offset: int = 0
        self._mouse_was_pressed: bool = False
        self._spawn_initial_ripples()

    def _spawn_initial_ripples(self) -> None:
        self.ripples.clear()
        count = self._rng.randint(MIN_RIPPLES, MAX_RIPPLES)
        for _ in range(count):
            self.ripples.append(self._spawn_ripple())

    def _spawn_ripple(self) -> Ripple:
        x = self._rng.uniform(30, 290)
        y = self._rng.uniform(WATER_Y + 5, WATER_Y + WATER_H - 15)
        color = self._rng.choice(RIPPLE_COLORS)
        vx = self._rng.choice([-RIPPLE_DRIFT_SPEED, RIPPLE_DRIFT_SPEED]) * self._rng.uniform(0.5, 1.5)
        return Ripple(x=x, y=y, color=color, vx=vx)

    def update(self) -> None:
        self._rainbow_offset = (pyxel.frame_count // 3) % len(RIPPLE_COLORS)
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.AIMING:
                self._update_aiming()
            case Phase.FLYING:
                self._update_flying()
            case Phase.SCORING:
                self._update_scoring()
            case Phase.GAME_OVER:
                self._update_game_over()

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.AIMING | Phase.FLYING | Phase.SCORING:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game_over()

    # ─── TITLE ────────────────────────────────────────────────

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.AIMING
            self._spawn_initial_ripples()

    def _draw_title(self) -> None:
        pyxel.cls(6)  # LIGHT_BLUE sky
        pyxel.rect(0, WATER_Y, SCREEN_W, WATER_H, 5)  # DARK_BLUE water
        pyxel.text(95, 30, "SKIP SURGE", 7)
        pyxel.text(55, 60, "Color-Match Stone Skipping", 3)
        pyxel.text(50, 100, "Click & hold to charge,", 7)
        pyxel.text(50, 110, "release to throw!", 7)
        pyxel.text(50, 130, "Hit same-color ripples to COMBO!", 8)
        pyxel.text(50, 145, "Wrong color = COMBO RESET + HEAT", 10)
        pyxel.text(50, 160, "COMBO x4 = SUPER SKIP!", 3)
        pyxel.text(50, 175, "(Rainbow, 3x Score, Extra Bounces)", 11)
        blink = (pyxel.frame_count // 20) % 2 == 0
        pyxel.text(85, 210, "Press SPACE to Start", 7 if blink else 0)

    # ─── AIMING ──────────────────────────────────────────────

    def _update_aiming(self) -> None:
        self._update_super_mode()
        self._update_particles()
        self._update_float_texts()
        self._update_ripples()
        self._update_heat()

        if self.game_timer <= 0 or self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        self.game_timer -= 1

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            self.aim_power = min(POWER_MAX, self.aim_power + POWER_CHARGE_SPEED)
            self._mouse_was_pressed = True
        elif self._mouse_was_pressed:
            self._throw_stone()
            self._mouse_was_pressed = False
        else:
            self.aim_power = POWER_MIN

    def _throw_stone(self) -> None:
        power = self.aim_power
        factor = power * 0.02
        vx = factor * math.cos(THROW_ANGLE)
        vy = -factor * math.sin(THROW_ANGLE)
        self.stone = Stone(
            x=160.0,
            y=230.0,
            vx=vx,
            vy=vy,
            alive=True,
            super_mode=self.super_mode,
            super_timer=self.super_timer,
            combo_color=-1,
        )
        self.throw_count += 1
        self.phase = Phase.FLYING
        self.aim_power = POWER_MIN

    # ─── FLYING ──────────────────────────────────────────────

    def _update_flying(self) -> None:
        self._update_super_mode()
        self._update_particles()
        self._update_float_texts()
        self._update_ripples()

        if self.stone is None:
            self.phase = Phase.AIMING
            return

        # If super mode on player side expired but stone still has it, tick stone's too
        if not self.super_mode and self.stone.super_mode:
            self.stone.super_timer -= 1
            if self.stone.super_timer <= 0:
                self.stone.super_mode = False

        stone = self.stone
        stone.vy += STONE_GRAVITY
        stone.x += stone.vx
        stone.y += stone.vy

        # Check collision with ripples
        bounced_this_frame = False
        for r in self.ripples:
            if not r.active:
                continue
            dx = stone.x - r.x
            dy = stone.y - r.y
            dist = math.hypot(dx, dy)
            if dist < r.radius + 4 and stone.vy > 0:
                self._process_skip(stone, r)
                r.active = False
                bounced_this_frame = True
                break

        if not bounced_this_frame:
            # Check sink condition
            if stone.vy > 0 and stone.y > WATER_Y + 20 and abs(stone.vy) < 2.5:
                self._stone_sink()

        # Also sink if stone goes too far off screen
        if stone.y > SCREEN_H + 20:
            self._stone_sink()
        if stone.x < -20 or stone.x > SCREEN_W + 20:
            self._stone_sink()

    def _process_skip(self, stone: Stone, ripple: Ripple) -> None:
        stone.bounces += 1

        match = self.super_mode or stone.super_mode or stone.combo_color == -1 or stone.combo_color == ripple.color

        if match:
            if stone.combo_color == -1:
                stone.combo_color = ripple.color
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                stone.super_mode = True
                stone.super_timer = SUPER_DURATION

            score_gain = self._compute_score(self.combo, stone.bounces, self.super_mode or stone.super_mode)
            self.score += score_gain

            ft = FloatText(stone.x, stone.y - 8, f"+{score_gain}", 45, 10 if self.super_mode else ripple.color)
            self.float_texts.append(ft)
        else:
            self.combo = 0
            stone.combo_color = ripple.color
            self.heat = min(MAX_HEAT, self.heat + HEAT_PER_WRONG)
            ft = FloatText(stone.x, stone.y - 8, "MISS", 30, 8)
            self.float_texts.append(ft)

        # Bounce physics
        vy_factor = SUPER_BOUNCE_VY_FACTOR if (self.super_mode or stone.super_mode) else BOUNCE_VY_FACTOR
        vx_factor = SUPER_BOUNCE_VX_FACTOR if (self.super_mode or stone.super_mode) else BOUNCE_VX_FACTOR
        stone.vy = -abs(stone.vy) * vy_factor
        stone.vx *= vx_factor

        # Particles
        self._spawn_splash_particles(stone.x, stone.y, ripple.color)
        self._spawn_respawn_ripple()

    def _spawn_splash_particles(self, x: float, y: float, color: int) -> None:
        count = 8 if (self.super_mode) else 6
        for _ in range(count):
            angle = self._rng.uniform(0, 2 * math.pi)
            speed = self._rng.uniform(0.5, 2.5)
            p = Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(15, 30),
                color=color,
                size=self._rng.randint(1, 2),
            )
            self.particles.append(p)

    def _spawn_respawn_ripple(self) -> None:
        new_ripple = self._spawn_ripple()
        new_ripple.active = False
        # Store respawn timer as a negative value so we can track it
        # Actually, let's use a simple timer list
        self.ripples.append(new_ripple)

    def _stone_sink(self) -> None:
        if self.stone is not None and self.stone.bounces == 0:
            self.heat = min(MAX_HEAT, self.heat + HEAT_PER_MISS)
            self.combo = 0
        self.stone = None
        self.phase = Phase.SCORING
        self._scoring_countdown = SCORING_DELAY

    def _compute_score(self, combo: int, bounces: int, super_mode: bool) -> int:
        base = 10
        multiplier = combo + 1
        if super_mode:
            multiplier *= 3
        return base * multiplier

    # ─── SCORING ─────────────────────────────────────────────

    def _update_scoring(self) -> None:
        self._update_super_mode()
        self._update_particles()
        self._update_float_texts()
        self._update_ripples()
        self._update_heat()

        if self.game_timer <= 0 or self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        self.game_timer -= 1
        self._scoring_countdown -= 1
        if self._scoring_countdown <= 0:
            self.phase = Phase.AIMING
            self.aim_power = POWER_MIN
            self._mouse_was_pressed = False

    # ─── GAME OVER ───────────────────────────────────────────

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_float_texts()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.AIMING
            self._spawn_initial_ripples()

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        pyxel.text(120, 40, "GAME OVER", 8)
        pyxel.text(105, 70, f"Score: {self.score}", 7)
        pyxel.text(95, 90, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(95, 110, f"Throws: {self.throw_count}", 7)
        reason = "HEAT Overload" if self.heat >= MAX_HEAT else "Time Up"
        pyxel.text(100, 130, f"Reason: {reason}", 6)
        blink = (pyxel.frame_count // 20) % 2 == 0
        pyxel.text(85, 180, "Press SPACE to Retry", 7 if blink else 0)

    # ─── DRAW GAME ───────────────────────────────────────────

    def _draw_game(self) -> None:
        pyxel.cls(6)  # LIGHT_BLUE sky
        self._draw_water()
        self._draw_ripples()
        self._draw_stone()
        self._draw_particles()
        self._draw_float_texts()
        self._draw_hud()
        if self.phase == Phase.AIMING:
            self._draw_power_bar()

    def _draw_water(self) -> None:
        # Water fill
        pyxel.rect(0, WATER_Y, SCREEN_W, WATER_H, 5)
        # Wavy line at top of water
        for x in range(0, SCREEN_W, 2):
            offset = int(math.sin((x + pyxel.frame_count * 0.5) * 0.05) * 3)
            pyxel.pset(x, WATER_Y + offset, 12)  # CYAN sparkle
        # Darker lines
        pyxel.rect(0, WATER_Y + WATER_H - 2, SCREEN_W, 2, 1)

    def _draw_ripples(self) -> None:
        for r in self.ripples:
            if not r.active:
                continue
            # Outer ring
            pyxel.circb(int(r.x), int(r.y), int(r.radius), r.color)
            # Inner ring
            pyxel.circb(int(r.x), int(r.y), int(r.radius) - 4, r.color)
            # Center dot
            pyxel.pset(int(r.x), int(r.y), 7 if r.color == 5 else 15)

    def _draw_stone(self) -> None:
        if self.stone is None or not self.stone.alive:
            return
        s = self.stone
        stone_color = 13  # GRAY
        if s.super_mode or self.super_mode:
            stone_color = RIPPLE_COLORS[self._rainbow_offset]
        # Draw as small ellipse (6x4)
        pyxel.elli(int(s.x), int(s.y), 6, 4, stone_color)
        # Highlight
        pyxel.elli(int(s.x - 1), int(s.y - 1), 3, 2, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                alpha_phase = (pyxel.frame_count // 4) % 2
                if p.life > 10 or alpha_phase == 0:
                    pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_float_texts(self) -> None:
        for ft in self.float_texts:
            if ft.life > 0:
                alpha_phase = (pyxel.frame_count // 4) % 2
                if ft.life > 20 or alpha_phase == 0:
                    pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 16, 0)

        pyxel.text(4, 2, f"SCORE:{self.score}", 7)

        combo_color = 10 if self.combo >= COMBO_THRESHOLD else 7
        pyxel.text(100, 2, f"COMBO:{self.combo}", combo_color)

        # HEAT bar
        pyxel.text(170, 2, "HEAT", 7)
        heat_w = 40
        pyxel.rectb(205, 1, heat_w + 2, 10, 7)
        heat_fill = int(self.heat * heat_w / MAX_HEAT)
        if heat_fill > 0:
            heat_col = 8 if self.heat >= 70 else (9 if self.heat >= 30 else 3)
            pyxel.rect(206, 2, heat_fill, 8, heat_col)

        secs = self.game_timer // 60
        time_col = 8 if secs <= 15 else 7
        pyxel.text(270, 2, f"T:{secs}", time_col)

        if self.super_mode:
            super_secs = self.super_timer // 60 + 1
            pyxel.text(110, 12, f"SUPER {super_secs}s", RIPPLE_COLORS[self._rainbow_offset])

    def _draw_power_bar(self) -> None:
        # Power bar on left side
        bar_x = 6
        bar_y = 30
        bar_h = 100
        bar_w = 10

        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 7)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 0)

        fill_h = int(self.aim_power * bar_h / POWER_MAX)

        # Color gradient: bottom (low) = GREEN, middle = YELLOW, top (high) = RED
        if fill_h > 0:
            for i in range(fill_h):
                y = bar_y + bar_h - 1 - i
                ratio = i / bar_h
                if ratio < 0.5:
                    col = 3  # GREEN
                elif ratio < 0.75:
                    col = 10  # YELLOW
                else:
                    col = 8  # RED
                pyxel.rect(bar_x, y, bar_w, 1, col)

        pyxel.text(bar_x - 2, bar_y + bar_h + 4, "PWR", 7)

    # ─── HELPERS ─────────────────────────────────────────────

    def _update_super_mode(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for ft in self.float_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    def _update_ripples(self) -> None:
        for r in self.ripples:
            if r.active:
                r.update()
        # Reactivate ripples that were deactivated
        for r in self.ripples:
            if not r.active:
                if self._rng.random() < 1.0 / (RIPPLE_RESPAWN_MIN + RIPPLE_RESPAWN_MAX * 0.5):
                    r.active = True

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            if self.phase in (Phase.AIMING, Phase.SCORING):
                self.phase = Phase.GAME_OVER
                return
        self.heat = max(0.0, self.heat - HEAT_DECAY)


if __name__ == "__main__":
    Game()
