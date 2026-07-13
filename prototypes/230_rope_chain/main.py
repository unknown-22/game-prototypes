"""230_rope_chain — Jump Rope Color-Match COMBO Chain Game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──
SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 200
PLAYER_X = 160
PLAYER_W = 16
PLAYER_H = 16
ROPE_PIVOT_X = 160
ROPE_PIVOT_Y = 60
ROPE_LENGTH = 160
GRAVITY = 0.4
JUMP_VY = -7.0
MAX_HEAT = 100.0
HEAT_MISMATCH = 15.0
HEAT_ROPE_HIT = 25.0
HEAT_DECAY = 0.02
GAME_DURATION = 60 * 60
SUPER_DURATION = 300
SUPER_COMBO_THRESHOLD = 4
STUN_DURATION = 20
COLOR_INTERVAL_START = 90
COLOR_INTERVAL_END = 40
ROPE_SPEED_START = 0.04
ROPE_SPEED_END = 0.10
MAX_ROPE_ANGLE = math.pi / 3

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

JUMP_COLORS = [RED, LIME, DARK_BLUE, YELLOW]
RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]


# ── Data Classes ──
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


# ── Phase Enum ──
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ──
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ROPE CHAIN")
        self.rng = random.Random()
        self.reset()
        self.phase = Phase.TITLE
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.rope_angle = 0.0
        self._rope_phase = math.pi / 2
        self.rope_speed = ROPE_SPEED_START
        self.player_y = float(GROUND_Y)
        self.player_vy = 0.0
        self.is_jumping = False
        self.jump_color = 0
        self.current_color = 0
        self.color_timer = COLOR_INTERVAL_START
        self.color_interval = COLOR_INTERVAL_START
        self.super_timer = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.stun_timer = 0
        self._pass_cooldown = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.phase = Phase.PLAYING

    # ── Update ──
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_timer()
            self._update_difficulty()
            self._update_color()
            self._update_rope()
            self._update_heat()
            self._update_stun()
            self._update_super()
            self._handle_input()
            self._update_player()
            self._check_rope_pass()
            self._update_particles()
            self._update_floating_texts()

    def _handle_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) and self.super_timer <= 0:
            self._apply_jump()

    def _update_difficulty(self) -> None:
        progress = 1.0 - self.timer / GAME_DURATION
        self.rope_speed = ROPE_SPEED_START + (ROPE_SPEED_END - ROPE_SPEED_START) * progress
        self.color_interval = COLOR_INTERVAL_START + (COLOR_INTERVAL_END - COLOR_INTERVAL_START) * progress

    def _update_color(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = int(self.color_interval)
            self.current_color = (self.current_color + 1) % 4

    def _update_rope(self) -> tuple[float, float]:
        self._rope_phase += self.rope_speed
        self.rope_angle = MAX_ROPE_ANGLE * math.sin(self._rope_phase)
        return self._rope_tip()

    def _rope_tip(self) -> tuple[float, float]:
        tip_x = ROPE_PIVOT_X + math.sin(self.rope_angle) * ROPE_LENGTH
        tip_y = ROPE_PIVOT_Y + math.cos(self.rope_angle) * ROPE_LENGTH
        return tip_x, tip_y

    def _update_player(self) -> None:
        if self.is_jumping:
            self.player_vy += GRAVITY
            self.player_y += self.player_vy
            if self.player_y >= GROUND_Y:
                self.player_y = float(GROUND_Y)
                self.player_vy = 0.0
                self.is_jumping = False

    def _apply_jump(self) -> bool:
        if self.player_y >= GROUND_Y and self.stun_timer <= 0:
            self.player_vy = JUMP_VY
            self.is_jumping = True
            self.jump_color = self.current_color
            return True
        return False

    def _check_rope_pass(self) -> str:
        if self._pass_cooldown > 0:
            self._pass_cooldown -= 1
            return "none"

        tip_x, tip_y = self._rope_tip()
        if tip_y >= 190 and abs(tip_x - PLAYER_X) < 20:
            self._pass_cooldown = 15

            if self.super_timer > 0:
                if not self.is_jumping:
                    self._apply_jump()
                self._on_successful_jump()
                return "jump"
            if self.is_jumping:
                self._on_successful_jump()
                return "jump"
            self._on_rope_hit()
            return "hit"
        return "none"

    def _on_successful_jump(self) -> None:
        is_super = self.super_timer > 0
        color_match = is_super or (self.jump_color == self.current_color)

        if color_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            score_mult = 3 if is_super else 1
            points = 10 * self.combo * score_mult
            self.score += points

            if not is_super and self.combo >= SUPER_COMBO_THRESHOLD:
                self.super_timer = SUPER_DURATION
                for _ in range(16):
                    c = RAINBOW_COLORS[self.rng.randint(0, len(RAINBOW_COLORS) - 1)]
                    self.particles.append(
                        Particle(
                            x=float(PLAYER_X) + self.rng.uniform(-8, 8),
                            y=self.player_y - PLAYER_H + self.rng.uniform(-8, 8),
                            vx=self.rng.uniform(-2, 2),
                            vy=self.rng.uniform(-3, -1),
                            life=20,
                            color=c,
                            size=2,
                        )
                    )
                self.floating_texts.append(
                    FloatingText(
                        x=float(PLAYER_X),
                        y=self.player_y - PLAYER_H - 8,
                        text="SUPER!",
                        life=60,
                        color=RAINBOW_COLORS[0],
                    )
                )

            party_color = JUMP_COLORS[self.current_color] if is_super else JUMP_COLORS[self.jump_color]
            for _ in range(8):
                self.particles.append(
                    Particle(
                        x=float(PLAYER_X) + self.rng.uniform(-6, 6),
                        y=self.player_y - PLAYER_H + self.rng.uniform(-6, 6),
                        vx=self.rng.uniform(-1.5, 1.5),
                        vy=self.rng.uniform(-2.5, -0.5),
                        life=15,
                        color=party_color,
                        size=2,
                    )
                )
            self.floating_texts.append(
                FloatingText(
                    x=float(PLAYER_X),
                    y=self.player_y - PLAYER_H - 4,
                    text=f"+{points}",
                    life=30,
                    color=party_color,
                )
            )
        else:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + HEAT_MISMATCH)
            for _ in range(4):
                self.particles.append(
                    Particle(
                        x=float(PLAYER_X) + self.rng.uniform(-4, 4),
                        y=self.player_y - PLAYER_H + self.rng.uniform(-4, 4),
                        vx=self.rng.uniform(-1, 1),
                        vy=self.rng.uniform(-2, -1),
                        life=15,
                        color=GRAY,
                        size=2,
                    )
                )
            self.floating_texts.append(
                FloatingText(
                    x=float(PLAYER_X),
                    y=self.player_y - PLAYER_H - 4,
                    text="MISS!",
                    life=30,
                    color=RED,
                )
            )

    def _on_rope_hit(self) -> None:
        self.heat = min(MAX_HEAT, self.heat + HEAT_ROPE_HIT)
        self.combo = 0
        self.stun_timer = STUN_DURATION
        for _ in range(8):
            self.particles.append(
                Particle(
                    x=float(PLAYER_X) + self.rng.uniform(-8, 8),
                    y=self.player_y - PLAYER_H + self.rng.uniform(-8, 8),
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-3, -1),
                    life=15,
                    color=RED,
                    size=2,
                )
            )
        self.floating_texts.append(
            FloatingText(
                x=float(PLAYER_X),
                y=self.player_y - PLAYER_H - 4,
                text="-25 HEAT!",
                life=30,
                color=ORANGE,
            )
        )

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_stun(self) -> None:
        if self.stun_timer > 0:
            self.stun_timer -= 1

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.combo = 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.15
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Draw ──
    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.PLAYING:
            self._draw_game()

    def _draw_title(self) -> None:
        self._text_center(80, "ROPE CHAIN", LIME)
        self._text_center(100, "Jump Rope Color-Match", WHITE)
        self._text_center(120, "Match colors, build combos!", GRAY)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(160, "Press SPACE to start", YELLOW)

    def _draw_game_over(self) -> None:
        self._text_center(80, "GAME OVER", RED)
        self._text_center(110, f"Score: {self.score}", WHITE)
        self._text_center(130, f"Max Combo: x{self.max_combo}", YELLOW)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(170, "Press SPACE to retry", GRAY)

    def _draw_game(self) -> None:
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, GRAY)
        self._draw_rope()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_rope(self) -> None:
        tip_x, tip_y = self._rope_tip()
        if self.super_timer > 0:
            color = RAINBOW_COLORS[(pyxel.frame_count // 5) % len(RAINBOW_COLORS)]
        else:
            color = WHITE
        pyxel.line(ROPE_PIVOT_X, ROPE_PIVOT_Y, int(tip_x), int(tip_y), color)

    def _draw_player(self) -> None:
        size = 20 if self.super_timer > 0 else PLAYER_W
        half = size // 2
        top = int(self.player_y - size)

        if self.super_timer > 0:
            color = RAINBOW_COLORS[(pyxel.frame_count // 5) % len(RAINBOW_COLORS)]
        elif self.stun_timer > 0 and (pyxel.frame_count // 4) % 2 == 0:
            color = GRAY
        else:
            color = JUMP_COLORS[self.jump_color]

        pyxel.rect(PLAYER_X - half, top, size, size, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(130, 4, f"COMBO: x{self.combo}", YELLOW)
        pyxel.text(260, 4, f"TIME: {self.timer // 60}", WHITE)
        pyxel.text(200, 4, "HEAT", WHITE)
        pyxel.rect(200, 8, 60, 4, GRAY)
        pyxel.rect(200, 8, int(60 * self.heat / MAX_HEAT), 4, RED)
        pyxel.rect(300, 16, 8, 8, JUMP_COLORS[self.current_color])

        if self.super_timer > 0:
            color = RAINBOW_COLORS[(pyxel.frame_count // 5) % len(RAINBOW_COLORS)]
            self._text_center(30, "SUPER!", color)

    # ── Utility ──
    def _text_center(self, y: int, text: str, color: int) -> None:
        x = (SCREEN_W - len(text) * pyxel.FONT_WIDTH) // 2
        pyxel.text(x, y, text, color)


if __name__ == "__main__":
    Game()
