"""AQUA SURGE -- Water Slide Racing Prototype (#290).

Core fun moment: 自分の色と一致するゲートを高速で通過しCOMBOを繋ぎ、
SUPER SLIDEで虹色になりながら一気に得点を稼ぐのが面白い
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 60
GAME_TIME = 3600

PLAYER_FIXED_Y = 100
PLAYER_RADIUS = 8

LANE_X: list[int] = [80, 160, 240]
LANE_W = 60
LANE_HALF = 30

GATE_COLORS: tuple[int, int, int, int] = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
GATE_W = 50
GATE_H = 12
GATE_PASS_THRESHOLD = 14

COMBO_FOR_SUPER = 4
SUPER_DURATION = 300
SUPER_SCORE_MULTIPLIER = 3

HEAT_MISMATCH = 15.0
HEAT_PASSIVE = 0.02
HEAT_DECAY = -0.02
HEAT_MAX = 100.0

SPEED_START = 1.5
SPEED_END = 4.0
GATE_INTERVAL_START = 90
GATE_INTERVAL_END = 30
COLOR_CYCLE_START = 20
COLOR_CYCLE_END = 12

LANE_SWITCH_COOLDOWN = 8

SCORE_BASE = 10

RAINBOW: tuple[int, ...] = (8, 9, 10, 11, 12, 6, 14, 15)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gate:
    lane: int
    y: float
    color: int
    passed: bool = False


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


@dataclass
class WakeDot:
    x: float
    y: float
    life: int


class Game:
    def __init__(self) -> None:
        self.rng = random.Random()
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = GAME_TIME
        self.best_score = 0

        self.lane = 1
        self.color_index = 0
        self.color_timer = COLOR_CYCLE_START
        self.lane_cooldown = 0
        self.scroll_y = 0.0
        self.speed = SPEED_START
        self.gate_spawn_timer = 0
        self._elapsed_frames = 0
        self._game_over_reason = ""

        self.gates: list[Gate] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.wake_dots: list[WakeDot] = []
        self.rainbow_tick = 0

    def reset(self) -> None:
        best = self.best_score
        self._init_state()
        self.best_score = best
        self.rng = random.Random()
        self.phase = Phase.PLAYING

    @property
    def is_super(self) -> bool:
        return self.super_timer > 0

    @property
    def current_color(self) -> int:
        return GATE_COLORS[self.color_index % len(GATE_COLORS)]

    def _progress(self) -> float:
        elapsed = GAME_TIME - self.timer
        return min(elapsed / GAME_TIME, 1.0)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _player_x(self) -> int:
        return LANE_X[self.lane]

    # ── Gate spawning ─────────────────────────────────────────────────────

    def _spawn_gate(self) -> None:
        lane = self.rng.randint(0, 2)
        color = self.rng.choice(GATE_COLORS)
        spawn_y = self.scroll_y + SCREEN_H + 20
        self.gates.append(Gate(lane=lane, y=spawn_y, color=color))

    # ── Gate update ───────────────────────────────────────────────────────

    def _update_gates(self) -> None:
        for gate in self.gates:
            gate.y -= self.speed
        self.gates = [g for g in self.gates if g.y > self.scroll_y - GATE_H]

    # ── Gate pass check ───────────────────────────────────────────────────

    def _check_gate_pass(self) -> None:
        for gate in self.gates:
            if gate.passed:
                continue
            if gate.lane != self.lane:
                continue
            if abs(gate.y - PLAYER_FIXED_Y) > GATE_PASS_THRESHOLD:
                continue
            gate.passed = True
            self._on_gate_pass(gate)

    def _on_gate_pass(self, gate: Gate) -> None:
        matched = self.is_super or (gate.color == self.current_color)
        multiplier = SUPER_SCORE_MULTIPLIER if self.is_super else 1

        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            points = int(SCORE_BASE * self.combo * multiplier)
            self.score += points

            self.floating_texts.append(FloatingText(
                float(PLAYER_FIXED_Y - 20),
                float(PLAYER_FIXED_Y - 20),
                f"+{points}",
                40, 7,
            ))
            self.floating_texts.append(FloatingText(
                float(PLAYER_FIXED_Y + 5),
                float(PLAYER_FIXED_Y + 5),
                f"COMBO x{self.combo}",
                40, 9,
            ))

            if self.is_super:
                self._spawn_particles(
                    self._player_x(), PLAYER_FIXED_Y,
                    self.rng.choice(RAINBOW), 20, 30
                )
            else:
                self._spawn_particles(
                    self._player_x(), PLAYER_FIXED_Y,
                    gate.color, 8, 20
                )

            if self.combo >= COMBO_FOR_SUPER and not self.is_super:
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self._spawn_particles(
                self._player_x(), PLAYER_FIXED_Y,
                8, 4, 10
            )
            self.floating_texts.append(FloatingText(
                float(PLAYER_FIXED_Y - 10),
                float(PLAYER_FIXED_Y - 10),
                "MISS!",
                30, 8,
            ))

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.floating_texts.append(FloatingText(
            SCREEN_W // 2, SCREEN_H // 2 - 30,
            "SUPER SLIDE!",
            60, 10,
        ))

    # ── Color cycle ───────────────────────────────────────────────────────

    def _update_color_cycle(self) -> None:
        interval = int(self._lerp(COLOR_CYCLE_START, COLOR_CYCLE_END, self._progress()))
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_index = (self.color_index + 1) % len(GATE_COLORS)
            self.color_timer = interval

    # ── Heat ──────────────────────────────────────────────────────────────

    def _update_heat(self) -> None:
        if self.is_super:
            return
        self.heat += HEAT_PASSIVE
        if self.heat > 0:
            self.heat = max(0.0, self.heat + HEAT_DECAY)
        if self.heat < 0:
            self.heat = 0.0

    # ── Difficulty ────────────────────────────────────────────────────────

    def _update_difficulty(self) -> None:
        self.speed = self._lerp(SPEED_START, SPEED_END, self._progress())

    # ── Particles ─────────────────────────────────────────────────────────

    def _spawn_particles(self, x: int, y: int, color: int, count: int, life: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 4.0)
            self.particles.append(Particle(
                x=float(x), y=float(y),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life, color=color, size=2,
            ))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life <= 0:
                continue
            p.vy += 0.15
            p.x += p.vx
            p.y += p.vy
            alive.append(p)
        self.particles = alive

    # ── Floating text ─────────────────────────────────────────────────────

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.life -= 1
            if ft.life <= 0:
                continue
            ft.y -= 0.6
            alive.append(ft)
        self.floating_texts = alive

    # ── Wake / ghost trail ────────────────────────────────────────────────

    def _update_ghost_trail(self) -> None:
        if self._elapsed_frames % 3 == 0:
            self.wake_dots.append(WakeDot(
                x=float(self._player_x()),
                y=float(PLAYER_FIXED_Y + 4),
                life=30,
            ))
        alive: list[WakeDot] = []
        for w in self.wake_dots:
            w.life -= 1
            if w.life <= 0:
                continue
            alive.append(w)
        self.wake_dots = alive

    # ── Scroll ────────────────────────────────────────────────────────────

    def _update_scroll(self) -> None:
        self.scroll_y += self.speed

    # ── Update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self._elapsed_frames += 1
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._end_game("Time is up!")
            return

        if self.lane_cooldown > 0:
            self.lane_cooldown -= 1

        self._update_scroll()
        self._update_difficulty()
        self._update_color_cycle()
        self._update_gates()
        self._check_gate_pass()
        self._update_heat()
        self._update_ghost_trail()
        self._update_particles()
        self._update_floating_texts()

        if self.heat >= HEAT_MAX:
            self._end_game("OVERHEAT!")
            return

        if self.super_timer > 0:
            self.super_timer -= 1
            self.rainbow_tick = (self.rainbow_tick + 1) % 5

        gate_interval = int(self._lerp(GATE_INTERVAL_START, GATE_INTERVAL_END, self._progress()))
        self.gate_spawn_timer -= 1
        if self.gate_spawn_timer <= 0:
            self.gate_spawn_timer = gate_interval
            self._spawn_gate()

    def _end_game(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        self._game_over_reason = reason
        if self.score > self.best_score:
            self.best_score = self.score

    # ── Input handling (called from App) ──────────────────────────────────

    def handle_left(self) -> None:
        if self.lane_cooldown > 0:
            return
        if self.lane > 0:
            self.lane -= 1
            self.lane_cooldown = LANE_SWITCH_COOLDOWN

    def handle_right(self) -> None:
        if self.lane_cooldown > 0:
            return
        if self.lane < 2:
            self.lane += 1
            self.lane_cooldown = LANE_SWITCH_COOLDOWN

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(5)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 60, "AQUA SURGE", 7)
        pyxel.text(SCREEN_W // 2 - 55, 80, "Water Slide Racing", 6)
        pyxel.text(SCREEN_W // 2 - 48, 110, "ARROWS: Switch lanes", 7)
        pyxel.text(SCREEN_W // 2 - 68, 122, "Match your color with gates!", 12)
        pyxel.text(SCREEN_W // 2 - 60, 134, "COMBO x4 = SUPER SLIDE!", 10)
        pyxel.text(SCREEN_W // 2 - 58, 154, "HEAT 100 = Wipeout!", 8)
        pyxel.text(SCREEN_W // 2 - 55, 190, "PRESS SPACE TO START", 7)
        for i, color in enumerate(GATE_COLORS):
            x = 110 + i * 28
            pyxel.rect(x, 104, 16, 8, color)

    def _draw_playing(self) -> None:
        self._draw_water_background()
        self._draw_gates()
        self._draw_wake()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_super_overlay()

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, 0)
        pyxel.rectb(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, 7)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 40, "GAME OVER", 8)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 - 20, f"SCORE: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 - 5, f"BEST:  {self.best_score}", 10)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 + 15, self._game_over_reason, 8)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 60, SCREEN_H // 2 + 32, "PRESS SPACE TO RETRY", 12)

    def _draw_water_background(self) -> None:
        offset = int(self.scroll_y * 2) % 40
        for y in range(-40, SCREEN_H + 40, 40):
            draw_y = y + offset
            for x in range(0, SCREEN_W, 60):
                pyxel.text(x + 20, draw_y, "~", 6)
        for i, lx in enumerate(LANE_X):
            pyxel.rect(lx - LANE_HALF, 0, 1, SCREEN_H, 13)
            pyxel.rect(lx + LANE_HALF, 0, 1, SCREEN_H, 13)
        self._draw_water_ripples(offset)

    def _draw_water_ripples(self, offset: int) -> None:
        for y in range(0, SCREEN_H, 24):
            draw_y = (y + offset) % SCREEN_H
            for i, lx in enumerate(LANE_X):
                wave_x = lx + int((int(self.scroll_y * 3 + y) % 60) - 30)
                if LANE_X[i] - LANE_HALF < wave_x < LANE_X[i] + LANE_HALF:
                    pyxel.pset(wave_x, draw_y, 6)

    def _draw_gates(self) -> None:
        for gate in self.gates:
            screen_y = gate.y - self.scroll_y
            if screen_y < -GATE_H or screen_y > SCREEN_H:
                continue
            lx = LANE_X[gate.lane]
            gx = lx - GATE_W // 2
            gy = int(screen_y)
            pyxel.rect(gx, gy, GATE_W, GATE_H, gate.color)
            pyxel.rectb(gx, gy, GATE_W, GATE_H, 7)
            pyxel.rect(gx - 4, gy, 4, GATE_H, gate.color)
            pyxel.rect(gx + GATE_W, gy, 4, GATE_H, gate.color)

    def _draw_player(self) -> None:
        px = self._player_x()
        py = PLAYER_FIXED_Y
        if self.is_super:
            color = RAINBOW[self.rainbow_tick % len(RAINBOW)]
            pyxel.circb(px, py, PLAYER_RADIUS + 4, color)
            pyxel.circb(px, py, PLAYER_RADIUS + 6, color)
        else:
            color = self.current_color
        pyxel.circ(px, py, PLAYER_RADIUS, color)
        pyxel.circ(px, py, PLAYER_RADIUS - 4, 7)
        pyxel.circ(px + 2, py - 2, 2, 0)

    def _draw_wake(self) -> None:
        for w in self.wake_dots:
            alpha = w.life / 30
            if alpha < 0.1:
                continue
            color = 12 if alpha > 0.5 else 13
            pyxel.pset(int(w.x), int(w.y), color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30
            color = p.color if alpha > 0.3 else 13
            pyxel.pset(int(p.x), int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40
            if alpha < 0.15:
                continue
            color = ft.color if alpha > 0.5 else 13
            pyxel.text(int(self._player_x()) - len(ft.text) * 2, int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        combo_color = 10 if self.combo >= COMBO_FOR_SUPER else 9 if self.combo >= 2 else 7
        pyxel.text(SCREEN_W // 2 - 20, 4, f"COMBO x{self.combo}", combo_color)

        seconds = max(0, self.timer // FPS)
        time_color = 8 if seconds <= 10 else 7
        pyxel.text(SCREEN_W - 56, 4, f"TIME: {seconds}", time_color)

        bar_x = SCREEN_W // 2 - 30
        bar_y = 14
        bar_w = 60
        pyxel.rect(bar_x, bar_y, bar_w, 6, 13)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        heat_color = 9 if self.heat > 70 else 8
        pyxel.rect(bar_x, bar_y, fill_w, 6, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, 6, 7)
        pyxel.text(bar_x - 16, bar_y - 1, "H", 8)

        if self.is_super:
            sec = max(1, self.super_timer // FPS)
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H - 16, f"SUPER: {sec}s", 10)
        else:
            color_indicator_x = SCREEN_W - 20
            color_indicator_y = SCREEN_H - 16
            pyxel.rect(color_indicator_x, color_indicator_y, 12, 12, self.current_color)
            pyxel.rectb(color_indicator_x, color_indicator_y, 12, 12, 7)

    def _draw_super_overlay(self) -> None:
        if not self.is_super:
            return
        color = RAINBOW[self.rainbow_tick % len(RAINBOW)]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, color)
        pyxel.rectb(2, 2, SCREEN_W - 4, SCREEN_H - 4, color)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Aqua Surge", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
                g.handle_left()
            if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
                g.handle_right()
            g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
