"""KAYAK CHAIN -- Color-Match Kayak River Paddle COMBO chain game.

体験仮説:
  同じ色のゲートを連続で通り抜けてコンボを積み上げ、
  SUPER PADDLEが発動して虹色のまま暴れられる瞬間が最高に気持ちいい。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──
SCREEN_W = 320
SCREEN_H = 240

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

GATE_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "BLUE", "YEL")
RAINBOW_COLORS: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

PLAYFIELD_W = 280
PLAYFIELD_X = 20
PLAYFIELD_RIGHT = PLAYFIELD_X + PLAYFIELD_W

KAYAK_W = 20
KAYAK_H = 30
KAYAK_SPEED = 3.0
KAYAK_Y = 190

GATE_W = 40
GATE_H = 8
GATE_GAP = 24
GATE_MIN_SPACING = 30

SUPER_DURATION = 300
STUN_DURATION = 15
COMBO_THRESHOLD = 4

HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15.0
HEAT_MISS = 5.0

GAME_TIME = 60 * 60
COLOR_CYCLE_INITIAL = 90
COLOR_CYCLE_MIN = 40
SPAWN_INTERVAL_INITIAL = 60
SPAWN_INTERVAL_MIN = 20
SCROLL_SPEED_INITIAL = 1.0
SCROLL_SPEED_RATE = 0.03

BASE_SCORE = 10


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gate:
    x: float
    y: float
    color: int
    passed: bool = False
    width: int = GATE_W
    height: int = GATE_H


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    phase: Phase
    kayak_x: float
    kayak_y: float
    paddle_color_idx: int
    color_timer: int
    gates: list[Gate]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    score: int
    high_score: int
    combo: int
    max_combo: int
    heat: float
    super_timer: int
    stun_timer: int
    game_timer: int
    scroll_speed: float
    spawn_interval: int
    spawn_timer: int
    rng: random.Random

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="KAYAK CHAIN")
        self.rng = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.kayak_x = float(PLAYFIELD_X + PLAYFIELD_W // 2 - KAYAK_W // 2)
        self.kayak_y = float(KAYAK_Y)
        self.paddle_color_idx = 0
        self.color_timer = COLOR_CYCLE_INITIAL
        self.gates = []
        self.particles = []
        self.floating_texts = []
        self.score = 0
        self.high_score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.stun_timer = 0
        self.game_timer = GAME_TIME
        self.scroll_speed = SCROLL_SPEED_INITIAL
        self.spawn_interval = SPAWN_INTERVAL_INITIAL
        self.spawn_timer = SPAWN_INTERVAL_INITIAL

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.kayak_x = float(PLAYFIELD_X + PLAYFIELD_W // 2 - KAYAK_W // 2)
        self.kayak_y = float(KAYAK_Y)
        self.paddle_color_idx = 0
        self.color_timer = COLOR_CYCLE_INITIAL
        self.gates.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.stun_timer = 0
        self.game_timer = GAME_TIME
        self.scroll_speed = SCROLL_SPEED_INITIAL
        self.spawn_interval = SPAWN_INTERVAL_INITIAL
        self.spawn_timer = SPAWN_INTERVAL_INITIAL

    # ── Spawn ──
    def _spawn_gate(self) -> Gate:
        x = self.rng.uniform(PLAYFIELD_X, PLAYFIELD_RIGHT - GATE_W)
        color = self.rng.choice(GATE_COLORS)
        y = float(-GATE_H - self.rng.uniform(0, 40))
        return Gate(x=x, y=y, color=color)

    # ── Collision ──
    def _check_kayak_gate_collision(self, gate: Gate) -> bool:
        if gate.passed:
            return False
        return (
            self.kayak_x < gate.x + gate.width
            and self.kayak_x + KAYAK_W > gate.x
            and self.kayak_y < gate.y + gate.height
            and self.kayak_y + KAYAK_H > gate.y
        )

    def _handle_gate_pass(self, gate: Gate) -> None:
        gate.passed = True

        is_super = self.super_timer > 0
        is_match = is_super or (gate.color == GATE_COLORS[self.paddle_color_idx])

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 3 if is_super else 1
            gained = int(BASE_SCORE * self.combo * multiplier)
            self.score += gained

            pcolor = (
                self.rng.choice(RAINBOW_COLORS) if is_super else gate.color
            )
            self._spawn_particles(gate.x + gate.width / 2, gate.y + gate.height / 2, pcolor, 10)
            self.floating_texts.append(
                FloatingText(gate.x + gate.width / 2, gate.y - 4, f"+{gained}", pcolor, 35)
            )

            if self.combo >= COMBO_THRESHOLD and self.super_timer <= 0:
                self._activate_super()
            elif self.combo >= COMBO_THRESHOLD and self.super_timer > 0:
                self.super_timer = SUPER_DURATION
            if self.combo >= 2:
                self.floating_texts.append(
                    FloatingText(
                        gate.x + gate.width / 2, gate.y - 16,
                        f"COMBO x{self.combo}", YELLOW, 40,
                    )
                )
        else:
            self.combo = 0
            self.heat = min(self.heat + HEAT_MISMATCH, HEAT_MAX)
            self.stun_timer = STUN_DURATION
            self._spawn_particles(gate.x + gate.width / 2, gate.y + gate.height / 2, RED, 5)
            self.floating_texts.append(
                FloatingText(gate.x + gate.width / 2, gate.y - 4, "MISS!", RED, 35)
            )

    def _handle_gate_miss(self, gate: Gate) -> None:
        self.heat = min(self.heat + HEAT_MISS, HEAT_MAX)
        self.floating_texts.append(
            FloatingText(gate.x + gate.width / 2, float(SCREEN_H - 4), "MISS", GRAY, 30)
        )

    # ── Super ──
    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        for _ in range(20):
            c = self.rng.choice(RAINBOW_COLORS)
            self.particles.append(
                Particle(
                    x=self.kayak_x + KAYAK_W / 2 + self.rng.uniform(-15, 15),
                    y=self.kayak_y + KAYAK_H / 2 + self.rng.uniform(-10, 10),
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-3, -1),
                    color=c,
                    life=30,
                )
            )
        self.floating_texts.append(
            FloatingText(self.kayak_x + KAYAK_W / 2, self.kayak_y - 20, "SUPER!", PINK, 60)
        )

    # ── Heat ──
    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Difficulty ──
    def _update_difficulty(self) -> None:
        elapsed = GAME_TIME - self.game_timer
        elapsed_seconds = elapsed / 60
        self.scroll_speed = SCROLL_SPEED_INITIAL + elapsed_seconds * SCROLL_SPEED_RATE
        self.spawn_interval = max(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_INITIAL - int(elapsed_seconds // 10) * 5)
        self.color_timer = max(COLOR_CYCLE_MIN, COLOR_CYCLE_INITIAL - int(elapsed_seconds // 10) * 5)

    # ── Particles ──
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-1.5, 0.5)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, color=color, life=15 + self.rng.randrange(10))
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles[:] = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Update ──
    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

    def _update_title(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()

    def _update_game_over(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()

    def _update_playing(self) -> None:
        # Input
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.kayak_x -= KAYAK_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.kayak_x += KAYAK_SPEED
        self.kayak_x = max(
            float(PLAYFIELD_X),
            min(float(PLAYFIELD_RIGHT - KAYAK_W), self.kayak_x),
        )

        # Timer
        self.game_timer -= 1
        if self.game_timer <= 0:
            self._end_game()
            return

        # Color cycle
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.paddle_color_idx = (self.paddle_color_idx + 1) % 4
            self._update_difficulty()
            self.color_timer = max(COLOR_CYCLE_MIN, self.color_timer)

        # Super timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # Stun timer
        if self.stun_timer > 0:
            self.stun_timer -= 1

        # Scroll gates
        for gate in self.gates:
            gate.y += self.scroll_speed

        # Spawn
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.gates.append(self._spawn_gate())
            self.spawn_timer = self.spawn_interval

        # Check collisions
        if self.stun_timer <= 0:
            for gate in self.gates:
                if self._check_kayak_gate_collision(gate):
                    self._handle_gate_pass(gate)

        # Remove passed & off-screen gates
        remaining: list[Gate] = []
        for gate in self.gates:
            if gate.passed and gate.y + gate.height < 0:
                continue
            if gate.y > SCREEN_H:
                if not gate.passed:
                    self._handle_gate_miss(gate)
                continue
            remaining.append(gate)
        self.gates = remaining

        # Heat
        self._update_heat()
        if self.heat >= HEAT_MAX:
            self._end_game()
            return

        # Difficulty
        self._update_difficulty()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.high_score:
            self.high_score = self.score

    # ── Draw ──
    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_game()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, NAVY)
        self._text_center(40, "KAYAK CHAIN", WHITE)
        self._text_center(70, "Color-Match River Paddle", GRAY)
        self._text_center(100, "ARROWS / A,D to steer kayak", WHITE)
        self._text_center(115, "Paddle color cycles automatically", LIGHT_BLUE)
        self._text_center(130, "Match gate color to pass = COMBO", YELLOW)
        self._text_center(145, "Wrong color = HEAT + STUN", ORANGE)
        self._text_center(160, f"COMBO x{COMBO_THRESHOLD}+ = SUPER PADDLE (rainbow 3x)", PINK)
        self._text_center(175, "Survive 60 seconds!", WHITE)
        if self.high_score > 0:
            self._text_center(195, f"High Score: {self.high_score}", YELLOW)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(220, "Press SPACE to Start", GRAY)

    def _draw_game(self) -> None:
        # River background
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, NAVY)
        # River banks
        pyxel.rect(0, 0, PLAYFIELD_X, SCREEN_H, BROWN)
        pyxel.rect(PLAYFIELD_RIGHT, 0, SCREEN_W - PLAYFIELD_RIGHT, SCREEN_H, BROWN)
        # Bank lines
        pyxel.line(PLAYFIELD_X, 0, PLAYFIELD_X, SCREEN_H, DARK_BLUE)
        pyxel.line(PLAYFIELD_RIGHT, 0, PLAYFIELD_RIGHT, SCREEN_H, DARK_BLUE)

        # Water flow lines
        for i in range(5):
            ly = (pyxel.frame_count * 0.8 + i * 48) % 240
            pyxel.line(PLAYFIELD_X + 5, ly, PLAYFIELD_RIGHT - 5, ly, NAVY)
            pyxel.line(PLAYFIELD_X + 5, ly + 1, PLAYFIELD_RIGHT - 5, ly + 1, DARK_BLUE)

        # Gates
        self._draw_gates()

        # Kayak
        self._draw_kayak()

        # Particles
        self._draw_particles()

        # Floating texts
        self._draw_floating_texts()

        # HUD
        self._draw_hud()

        # Super border
        if self.super_timer > 0:
            bc = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, bc)

    def _draw_gates(self) -> None:
        for gate in self.gates:
            c = gate.color
            if self.super_timer > 0:
                c = RAINBOW_COLORS[(pyxel.frame_count // 4 + hash((gate.x, gate.y))) % len(RAINBOW_COLORS)]
            gx = int(gate.x)
            gy = int(gate.y)
            # Left bar
            pyxel.rect(gx, gy, GATE_GAP, gate.height, c)
            # Right bar
            pyxel.rect(gx + GATE_GAP + GATE_W, gy, GATE_W, gate.height, c)
            # Connecting lines
            pyxel.rect(gx, gy + gate.height // 2 - 1, GATE_GAP + GATE_W + GATE_W, 2, c)

    def _draw_kayak(self) -> None:
        kx = int(self.kayak_x)
        ky = int(self.kayak_y)

        # Kayak body
        pyxel.rect(kx, ky, KAYAK_W, KAYAK_H, DARK_BLUE)
        pyxel.rect(kx + 2, ky - 2, KAYAK_W - 4, 4, LIGHT_BLUE)
        pyxel.rect(kx + 2, ky + KAYAK_H - 2, KAYAK_W - 4, 4, LIGHT_BLUE)

        # Paddle indicator
        paddle_color = GATE_COLORS[self.paddle_color_idx]
        if self.super_timer > 0:
            paddle_color = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
        px = kx + KAYAK_W // 2 - 2
        py = ky - 10
        pyxel.rect(px, py, 4, 8, paddle_color)
        pyxel.rectb(px, py, 4, 8, WHITE)

        # Stun visual
        if self.stun_timer > 0 and (pyxel.frame_count // 4) % 2 == 0:
            pyxel.rectb(kx - 1, ky - 1, KAYAK_W + 2, KAYAK_H + 2, RED)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 5:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)
            else:
                pyxel.pset(int(p.x), int(p.y), GRAY)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life <= 0:
                continue
            alpha = ft.life / 40.0
            if alpha > 0.2:
                tw = len(ft.text) * pyxel.FONT_WIDTH
                pyxel.text(int(ft.x - tw / 2), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        # Combo
        combo_color = WHITE
        if self.combo >= COMBO_THRESHOLD or self.super_timer > 0:
            combo_color = RAINBOW_COLORS[(pyxel.frame_count // 3) % len(RAINBOW_COLORS)]
        elif self.combo >= 2:
            combo_color = LIME
        pyxel.text(4, 14, f"COMBO: x{self.combo}", combo_color)

        # Timer
        seconds = max(0, self.game_timer // 60)
        timer_color = WHITE if seconds > 10 else RED
        if seconds <= 10 and (pyxel.frame_count // 15) % 2 == 0:
            timer_color = 0  # blink off
        timer_str = f"TIME: {seconds:02d}"
        pyxel.text(SCREEN_W - len(timer_str) * 4 - 4, 4, timer_str, timer_color)

        # Heat bar
        bar_w = 80
        bar_h = 6
        bar_x = 4
        bar_y = SCREEN_H - 12
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        heat_fill = int(bar_w * (self.heat / HEAT_MAX))
        if self.heat < 40:
            hc = GREEN
        elif self.heat < 70:
            hc = ORANGE
        else:
            hc = RED
        pyxel.rect(bar_x, bar_y, heat_fill, bar_h, hc)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 2, f"HEAT {int(self.heat)}", WHITE)

        # Super timer
        if self.super_timer > 0:
            super_sec = self.super_timer / 60.0
            super_str = f"SUPER {super_sec:.1f}s"
            pyxel.text(SCREEN_W // 2 - len(super_str) * 4, 4, super_str, PINK)

        # Paddle color name
        name_str = COLOR_NAMES[self.paddle_color_idx]
        pyxel.text(SCREEN_W - len(name_str) * 4 - 4, SCREEN_H - 14, name_str, GATE_COLORS[self.paddle_color_idx])

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(40, 40, SCREEN_W - 80, SCREEN_H - 80, BLACK)
        pyxel.rectb(40, 40, SCREEN_W - 80, SCREEN_H - 80, RED)
        self._text_center(60, "GAME OVER", RED)
        self._text_center(90, f"Score: {self.score}", WHITE)
        self._text_center(110, f"Max COMBO: x{self.max_combo}", YELLOW)
        reason = "HEAT OVERLOAD!" if self.heat >= HEAT_MAX else "TIME UP!"
        self._text_center(135, reason, GRAY)
        self._text_center(160, f"Best: {self.high_score}", YELLOW)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(190, "Press SPACE to Retry", WHITE)

    # ── Utility ──
    def _text_center(self, y: int, text: str, color: int) -> None:
        x = (SCREEN_W - len(text) * pyxel.FONT_WIDTH) // 2
        pyxel.text(x, y, text, color)


if __name__ == "__main__":
    Game()
