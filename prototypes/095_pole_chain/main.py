from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

ZONE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]

WIDTH: int = 320
HEIGHT: int = 240

RUNWAY_Y: int = 180
RUNWAY_H: int = 20
PLAYER_FEET_Y: int = RUNWAY_Y
PLAYER_W: int = 10
PLAYER_H: int = 16
PLAYER_DRAW_Y: int = PLAYER_FEET_Y - PLAYER_H

BASE_SPEED: float = 1.5
SPEED_PER_COMBO: float = 0.5
BASE_VAULT: int = 80
VAULT_PER_COMBO: int = 15

RUNWAY_END_X: int = 200
BAR_X: int = RUNWAY_END_X + 15
BAR_W: int = 40
INITIAL_BAR_Y: int = 140
MIN_BAR_Y: int = 40
MAX_BAR_Y: int = 160
BAR_DECREASE: int = 8

SUPER_VAULT_COMBO: int = 4
SUPER_VAULT_SCORE_MULT: int = 3

MAX_ROUNDS: int = 10
MAX_HEAT: int = 5
MAX_COMBO: int = 20

VAULT_FRAMES: int = 60
RESULT_FRAMES: int = 30
SHAKE_FRAMES: int = 10

ZONE_MIN_X: int = 20
ZONE_MAX_X: int = int(RUNWAY_END_X - 24)
ZONE_MIN_GAP: int = 12
ZONE_MIN_W: int = 24
ZONE_MAX_W: int = 36
ZONE_COUNT_MIN: int = 3
ZONE_COUNT_MAX: int = 5

MATCH_COLOR_WEIGHT: float = 0.35


class Phase(Enum):
    TITLE = auto()
    RUNNING = auto()
    VAULTING = auto()
    RESULT = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Zone:
    x: float
    w: float
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.round: int = 1
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.player_x: float = float(ZONE_MIN_X)
        self.player_color: int = ZONE_COLORS[0]
        self.zones: list[Zone] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.bar_y: int = INITIAL_BAR_Y
        self.speed: float = BASE_SPEED
        self._vault_timer: int = 0
        self._vault_height: int = 0
        self._vault_cleared: bool = False
        self._shake_frames: int = 0
        self._shake_seed: int = 0
        self._result_timer: int = 0
        self._rng: random.Random = random.Random()
        self._title_flash: int = 0
        self._super_vault_active: bool = False

    def reset(self) -> None:
        self._init_state()

    # ------------------------------------------------------------------
    # Pure logic (headless-testable)
    # ------------------------------------------------------------------

    def _spawn_zones(self) -> None:
        count = self._rng.randint(ZONE_COUNT_MIN, ZONE_COUNT_MAX)
        self.zones.clear()
        x = float(ZONE_MIN_X)
        for _ in range(count):
            remaining = ZONE_MAX_X - x
            if remaining < ZONE_MIN_W:
                break
            # Random width within bounds
            max_w = min(ZONE_MAX_W, int(remaining))
            if max_w < ZONE_MIN_W:
                break
            w = float(self._rng.randint(ZONE_MIN_W, max_w))
            zone_x = x + float(self._rng.randint(0, max(0, int(remaining - w - ZONE_MIN_GAP))))
            # Pick color
            if self._rng.random() < MATCH_COLOR_WEIGHT:
                color = self.player_color
            else:
                available = [c for c in ZONE_COLORS if c != self.player_color]
                color = self._rng.choice(available)
            self.zones.append(Zone(x=zone_x, w=w, color=color))
            x = zone_x + w + float(self._rng.randint(ZONE_MIN_GAP, ZONE_MIN_GAP + 20))

    def _match_zone(self, color: int) -> bool:
        if color == self.player_color:
            self.combo = min(self.combo + 1, MAX_COMBO)
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.player_color = self._next_zone_color()
            self.speed = BASE_SPEED + self.combo * SPEED_PER_COMBO
            if self.combo >= SUPER_VAULT_COMBO:
                self._super_vault_active = True
            return True
        self.combo = 0
        self.player_color = self._next_zone_color()
        self.speed = BASE_SPEED
        self._super_vault_active = False
        return False

    def _next_zone_color(self) -> int:
        idx = ZONE_COLORS.index(self.player_color)
        return ZONE_COLORS[(idx + 1) % len(ZONE_COLORS)]

    def _compute_vault_height(self) -> int:
        h = BASE_VAULT + self.combo * VAULT_PER_COMBO
        if self._super_vault_active:
            h = max(h, self.bar_y + 10)
        return h

    def _is_super_vault(self) -> bool:
        return self.combo >= SUPER_VAULT_COMBO

    def _check_vault_clear(self, vault_height: int) -> bool:
        return vault_height >= self.bar_y

    def _advance_round(self) -> None:
        self.round += 1
        self.bar_y = max(MIN_BAR_Y, self.bar_y - BAR_DECREASE)
        self.combo = 0
        self.speed = BASE_SPEED
        self.player_x = float(ZONE_MIN_X)
        self.player_color = self._next_zone_color()
        self.zones.clear()
        self.particles.clear()
        self.floats.clear()
        self._vault_timer = 0
        self._vault_height = 0
        self._vault_cleared = False
        self._shake_frames = 0
        self._super_vault_active = False
        self._spawn_zones()
        self.phase = Phase.RUNNING

    def _is_game_over(self) -> bool:
        return self.heat >= MAX_HEAT or self.round > MAX_ROUNDS

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------

    def _start_running(self) -> None:
        self._spawn_zones()
        self.phase = Phase.RUNNING
        self.player_x = float(ZONE_MIN_X)
        self.combo = 0
        self.speed = BASE_SPEED
        self._super_vault_active = False

    def _start_vault(self) -> None:
        self._vault_height = self._compute_vault_height()
        self._vault_cleared = self._check_vault_clear(self._vault_height)
        self._vault_timer = 0
        self.phase = Phase.VAULTING

    def _start_result(self) -> None:
        if self._vault_cleared:
            mult = SUPER_VAULT_SCORE_MULT if self._super_vault_active else 1
            gained = 100 * max(1, self.combo) * mult
            self.score += gained
            self._spawn_floating_text(f"+{gained}", YELLOW, 40)
            if self._super_vault_active:
                self._spawn_floating_text("SUPER!", RED, 60)
                self._shake_frames = SHAKE_FRAMES
                self._shake_seed = self._rng.randint(0, 9999)
        else:
            self.heat += 1
            self._spawn_floating_text("MISS", GRAY, 40)
        self._result_timer = RESULT_FRAMES
        self.phase = Phase.RESULT

    def _maybe_end_round(self) -> None:
        if self._is_game_over():
            self.phase = Phase.GAME_OVER
        else:
            self._advance_round()

    # ------------------------------------------------------------------
    # Particle / floating text
    # ------------------------------------------------------------------

    def _spawn_particles(self, x: float, y: float, color: int, count: int, speed_range: tuple[float, float] = (0.5, 2.0)) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(*speed_range)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    life=self._rng.randint(8, 18),
                    color=color,
                )
            )

    def _spawn_celebration_particles(self) -> None:
        self._spawn_particles(BAR_X + BAR_W / 2, float(self.bar_y), YELLOW, 10, (1.0, 3.0))

    def _spawn_miss_particles(self) -> None:
        self._spawn_particles(BAR_X + BAR_W / 2, float(self.bar_y), GRAY, 3, (0.3, 1.0))

    def _spawn_floating_text(self, text: str, color: int, life: int = 30) -> None:
        self.floats.append(FloatingText(x=float(WIDTH // 2), y=float(HEIGHT // 2 - 20), text=text, color=color, life=life))

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.3
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y -= 0.6
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _update_shake(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
            try:
                shake_rng = random.Random(self._shake_seed + self._shake_frames)
                pyxel.camera(shake_rng.randint(-4, 4), shake_rng.randint(-4, 4))
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

    # ------------------------------------------------------------------
    # Phase-specific updates
    # ------------------------------------------------------------------

    def update_title(self) -> None:
        self._title_flash += 1
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.RUNNING
            self._spawn_zones()

    def update_running(self) -> None:
        self._update_particles()
        self._update_floats()

        self.player_x += self.speed

        if self.player_x >= RUNWAY_END_X:
            self._start_vault()
            return

        if pyxel.btnp(pyxel.KEY_RETURN):
            for zone in self.zones:
                if zone.x <= self.player_x <= zone.x + zone.w:
                    matched = self._match_zone(zone.color)
                    if matched:
                        self._spawn_particles(self.player_x, float(PLAYER_DRAW_Y + PLAYER_H // 2), zone.color, 3)
                        self._spawn_floating_text(f"+COMBO x{self.combo}", zone.color, 25)
                        if self._super_vault_active:
                            self._spawn_floating_text("SUPER READY!", YELLOW, 30)
                    else:
                        self._spawn_particles(self.player_x, float(PLAYER_DRAW_Y + PLAYER_H // 2), GRAY, 2)
                        self._spawn_floating_text("RESET", GRAY, 20)
                    break

    def update_vaulting(self) -> None:
        self._update_particles()
        self._update_floats()
        self._update_shake()

        self._vault_timer += 1

        if self._vault_timer == int(VAULT_FRAMES * 0.5):
            if self._vault_cleared:
                self._spawn_celebration_particles()
            else:
                self._spawn_miss_particles()

        if self._vault_timer >= VAULT_FRAMES:
            self._start_result()

    def update_result(self) -> None:
        self._update_particles()
        self._update_floats()
        self._update_shake()

        self._result_timer -= 1
        if self._result_timer <= 0:
            self._maybe_end_round()

    def update_game_over(self) -> None:
        self._update_particles()
        self._update_floats()
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    # ------------------------------------------------------------------
    # Global update
    # ------------------------------------------------------------------

    def update(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self.update_title()
            case Phase.RUNNING:
                self.update_running()
            case Phase.VAULTING:
                self.update_vaulting()
            case Phase.RESULT:
                self.update_result()
            case Phase.GAME_OVER:
                self.update_game_over()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw_runway(self) -> None:
        pyxel.rect(0, RUNWAY_Y, RUNWAY_END_X, RUNWAY_H, BROWN)
        pyxel.line(0, RUNWAY_Y, RUNWAY_END_X, RUNWAY_Y, WHITE)
        pyxel.line(RUNWAY_END_X, RUNWAY_Y, RUNWAY_END_X, RUNWAY_Y + RUNWAY_H, WHITE)

    def _draw_zones(self) -> None:
        for zone in self.zones:
            pyxel.rect(int(zone.x), RUNWAY_Y, int(zone.w), RUNWAY_H, zone.color)

    def _draw_bar(self) -> None:
        sx = BAR_X
        stand_y = RUNWAY_Y
        pole_top = self.bar_y + 5
        pyxel.line(sx, stand_y, sx, pole_top, WHITE)
        pyxel.line(sx + BAR_W, stand_y, sx + BAR_W, pole_top, WHITE)
        pyxel.line(sx, self.bar_y, sx + BAR_W, self.bar_y, WHITE)

    def _draw_player(self) -> None:
        if self.phase == Phase.VAULTING:
            return
        px = int(self.player_x)
        py = PLAYER_DRAW_Y
        if self._super_vault_active:
            c = YELLOW if (pyxel.frame_count // 4) % 2 == 0 else self.player_color
            pyxel.rect(px, py, PLAYER_W, PLAYER_H, c)
        else:
            pyxel.rect(px, py, PLAYER_W, PLAYER_H, self.player_color)
        pyxel.rectb(px, py, PLAYER_W, PLAYER_H, WHITE)

    def _draw_player_icon_during_vault(self) -> None:
        if self.phase != Phase.VAULTING:
            return
        t = self._vault_timer / VAULT_FRAMES
        vx = RUNWAY_END_X + t * 60
        vy = RUNWAY_Y - (self._vault_height * 4 * t * (1 - t))
        c = YELLOW if self._super_vault_active else self.player_color
        if self._super_vault_active and (pyxel.frame_count // 3) % 2 == 0:
            alt_idx = (pyxel.frame_count // 3) % len(ZONE_COLORS)
            c = ZONE_COLORS[alt_idx]
        pyxel.rect(int(vx), int(vy) - PLAYER_H, PLAYER_W, PLAYER_H, c)
        pyxel.rectb(int(vx), int(vy) - PLAYER_H, PLAYER_W, PLAYER_H, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            s = p.size
            pyxel.rect(int(p.x) - s // 2, int(p.y) - s // 2, s, s, p.color)

    def _draw_floats(self) -> None:
        for f in self.floats:
            alpha = f.life / 40.0
            c = f.color if alpha > 0.5 else GRAY
            offset = (40 - f.life) * 0.3
            pyxel.text(
                int(f.x) - len(f.text) * 2 + 2,
                int(f.y) - int(offset),
                f.text,
                c,
            )

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"ROUND {self.round}/{MAX_ROUNDS}", WHITE)
        pyxel.text(WIDTH // 2 - 20, 4, f"COMBO x{self.combo}", CYAN if self.combo >= 3 else WHITE)
        pyxel.text(WIDTH - 70, 4, f"SCORE {self.score}", YELLOW)

        heat_bar_x = 4
        heat_bar_y = HEIGHT - 12
        heat_bar_w = 100
        heat_bar_h = 6
        pyxel.rect(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, NAVY)
        fill = int(heat_bar_w * self.heat / MAX_HEAT)
        heat_color = RED if self.heat >= 3 else ORANGE
        pyxel.rect(heat_bar_x, heat_bar_y, fill, heat_bar_h, heat_color)
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, GRAY)
        pyxel.text(heat_bar_x + heat_bar_w + 4, heat_bar_y - 1, f"HEAT {self.heat}/{MAX_HEAT}", GRAY)

        speed_bar_x = WIDTH - 64
        speed_bar_y = HEIGHT - 12
        speed_bar_w = 60
        speed_bar_h = 6
        pyxel.rect(speed_bar_x, speed_bar_y, speed_bar_w, speed_bar_h, NAVY)
        max_speed = BASE_SPEED + MAX_COMBO * SPEED_PER_COMBO
        speed_fill = int(speed_bar_w * min(self.speed / max_speed, 1.0))
        pyxel.rect(speed_bar_x, speed_bar_y, speed_fill, speed_bar_h, LIME)
        pyxel.rectb(speed_bar_x, speed_bar_y, speed_bar_w, speed_bar_h, GRAY)
        pyxel.text(speed_bar_x - 22, speed_bar_y - 1, "SPD", GRAY)

    def _draw_vault_line(self) -> None:
        if self.phase in (Phase.VAULTING, Phase.RESULT):
            h_line = int(RUNWAY_Y - self._vault_height)
            col = LIME if self._vault_cleared else RED
            pyxel.line(RUNWAY_END_X, h_line, RUNWAY_END_X + 60, h_line, col)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(WIDTH // 2 - 30, 60, "POLE CHAIN", WHITE)
        pyxel.text(WIDTH // 2 - 50, 80, "Color-Match Pole Vault", GRAY)

        pyxel.text(WIDTH // 2 - 55, 110, "Run down the runway", WHITE)
        pyxel.text(WIDTH // 2 - 70, 125, "Press SPACE to match colors", WHITE)
        pyxel.text(WIDTH // 2 - 65, 140, "Build COMBO for higher vaults!", CYAN)
        pyxel.text(WIDTH // 2 - 40, 155, f"COMBO >= {SUPER_VAULT_COMBO} = SUPER VAULT!", YELLOW)

        if (self._title_flash // 15) % 2 == 0:
            pyxel.text(WIDTH // 2 - 35, 185, "PRESS SPACE", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(WIDTH // 2 - 30, 50, "GAME OVER", RED)

        reason = "TOO MUCH HEAT!" if self.heat >= MAX_HEAT else f"{MAX_ROUNDS} ROUNDS COMPLETE!"
        pyxel.text(WIDTH // 2 - len(reason) * 2, 75, reason, ORANGE)

        pyxel.text(WIDTH // 2 - 50, 100, f"Final Score: {self.score}", WHITE)
        pyxel.text(WIDTH // 2 - 40, 120, f"Max Combo: x{self.max_combo}", CYAN)
        pyxel.text(WIDTH // 2 - 45, 140, f"Rounds: {self.round}/{MAX_ROUNDS}", GRAY)

        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(WIDTH // 2 - 35, 170, "PRESS SPACE", WHITE)

        self._draw_particles()
        self._draw_floats()

    # ------------------------------------------------------------------
    # Phase-specific draws
    # ------------------------------------------------------------------

    def _draw_game_base(self) -> None:
        pyxel.cls(NAVY)
        self._draw_runway()
        self._draw_zones()
        self._draw_bar()
        self._draw_player()
        self._draw_player_icon_during_vault()
        self._draw_particles()
        self._draw_floats()
        self._draw_hud()
        self._draw_vault_line()

    def _draw_phase(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.RUNNING:
                self._draw_game_base()
            case Phase.VAULTING:
                self._draw_game_base()
            case Phase.RESULT:
                self._draw_game_base()
            case Phase.GAME_OVER:
                self._draw_game_over()

    def draw(self) -> None:
        self._draw_phase()


# ---------------------------------------------------------------------------
# App wrapper
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="POLE CHAIN", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
