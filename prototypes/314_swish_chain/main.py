import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel


# ---------------------------------------------------------------------------
# Color constants (raw ints)
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

BALL_COLORS = (RED, LIME, DARK_BLUE, YELLOW)


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Hoop:
    x: float
    y: float
    radius: int
    color: int
    multiplier: int


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    active: bool
    color: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    # ------------------------------------------------------------------ constants
    SCREEN_W = 320
    SCREEN_H = 240
    GRAVITY = 0.35
    SUPER_THRESHOLD = 4
    SUPER_DURATION = 300
    MAX_HEAT = 100.0
    LAUNCH_X = 160
    LAUNCH_Y = 210
    HOOP_Y = 70
    HOOP_RADIUS = 18
    HOOP_BASE_XS = (80, 160, 240)
    HOOP_MULTIPLIERS = (1, 2, 3)
    GAME_TIME = 3600
    HEAT_DECAY = 0.02

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="SWISH CHAIN", fps=60)
        pyxel.mouse(True)
        self.best_score = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ helpers
    @property
    def elapsed(self) -> int:
        return self.GAME_TIME - self.game_timer

    def _hoop_eff_x(self, hoop: Hoop) -> float:
        return hoop.x + math.sin(self.elapsed * 0.03 + hoop.x * 0.05) * self.drift_amp

    def _add_text(self, text: str, x: float, y: float, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 40, color))

    def _game_over(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        self.game_over_reason = reason
        self.best_score = max(self.best_score, self.score)

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        self.rng = random.Random(42)
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = self.GAME_TIME
        self.player_color_index = 0
        self.player_color = BALL_COLORS[0]
        self.cycle_interval = 20
        self.cycle_timer = self.cycle_interval
        self.respawn_delay = 30
        self.drift_amp = 0
        self.super_timer = 0
        self.super_active = False
        self.ball = Ball(
            float(self.LAUNCH_X), float(self.LAUNCH_Y), 0.0, 0.0, False, self.player_color
        )
        self.hoops = [
            Hoop(float(x), float(self.HOOP_Y), self.HOOP_RADIUS, self.rng.choice(BALL_COLORS), mult)
            for x, mult in zip(self.HOOP_BASE_XS, self.HOOP_MULTIPLIERS)
        ]
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.respawn_timer = 0
        self.aiming = False
        self.press_x = 0.0
        self.press_y = 0.0
        self.trail: list[tuple[float, float]] = []
        self.game_over_reason = ""
        self.best_score = getattr(self, "best_score", 0)

    # ------------------------------------------------------------------ update
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self._game_over("TIME UP")
            return

        self._update_difficulty()
        self._cycle_player_color()
        self._update_aim()
        self._update_super()
        self._update_ball()
        self._update_heat()
        self._update_effects()

    def _update_difficulty(self) -> None:
        self.cycle_interval = max(12, 20 - self.elapsed // 120)
        self.respawn_delay = max(15, 30 - self.elapsed // 150)
        self.drift_amp = min(8, self.elapsed // 300)

    def _cycle_player_color(self) -> None:
        self.cycle_timer -= 1
        if self.cycle_timer <= 0:
            self.player_color_index = (self.player_color_index + 1) % len(BALL_COLORS)
            self.player_color = BALL_COLORS[self.player_color_index]
            self.cycle_timer = self.cycle_interval

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.super_active = False
                self.combo = 0

    def _update_aim(self) -> None:
        if self.ball.active or self.respawn_timer > 0:
            self.aiming = False
            return

        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        if not self.aiming:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if abs(mx - self.ball.x) <= 40 and abs(my - self.ball.y) <= 40:
                    self.aiming = True
                    self.press_x = float(mx)
                    self.press_y = float(my)
            return

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            return

        raw_vx = (self.press_x - mx) * 0.10
        raw_vy = (self.press_y - my) * 0.10
        if abs(raw_vx) < 0.4 and abs(raw_vy) < 0.8:
            self.aiming = False
            return

        vx = max(-6.5, min(6.5, raw_vx))
        vy = max(-13.0, min(-3.0, raw_vy))
        self._launch(vx, vy)
        self.aiming = False

    def _launch(self, vx: float, vy: float) -> None:
        self.ball.x = float(self.LAUNCH_X)
        self.ball.y = float(self.LAUNCH_Y)
        self.ball.vx = vx
        self.ball.vy = vy
        self.ball.color = self.player_color
        self.ball.active = True
        self.trail = []

    def _update_physics(self) -> None:
        self.ball.vy += self.GRAVITY
        self.ball.x += self.ball.vx
        self.ball.y += self.ball.vy

    def _update_ball(self) -> None:
        if not self.ball.active:
            if self.respawn_timer > 0:
                self.respawn_timer -= 1
                if self.respawn_timer == 0:
                    self.ball.x = float(self.LAUNCH_X)
                    self.ball.y = float(self.LAUNCH_Y)
            return

        prev_y = self.ball.y
        self._update_physics()

        self.trail.append((self.ball.x, self.ball.y))
        if len(self.trail) > 20:
            self.trail.pop(0)

        if self.ball.vy > 0:
            for hoop in self.hoops:
                eff_x = self._hoop_eff_x(hoop)
                if prev_y <= hoop.y < self.ball.y:
                    result = self._resolve_shot(hoop, eff_x)
                    if result is not None:
                        break

        if self.ball.active and (
            self.ball.y > self.SCREEN_H + 8
            or self.ball.x < -20
            or self.ball.x > self.SCREEN_W + 20
        ):
            self.heat += 15
            self.combo = 0
            self.ball.active = False
            self.respawn_timer = self.respawn_delay
            self._add_text("AIRBALL", self.ball.x, self.ball.y - 8, RED)

    def _resolve_shot(self, hoop: Hoop, eff_x: float) -> str | None:
        dx = abs(self.ball.x - eff_x)
        if dx <= hoop.radius - 2:
            if hoop.color == self.ball.color or self.super_active:
                return self._swish(hoop, eff_x)
            return self._clank(hoop, eff_x)
        if dx <= hoop.radius + 4:
            return self._rim_out(hoop, eff_x)
        return None

    def _swish(self, hoop: Hoop, eff_x: float) -> str:
        self.combo += 1
        mult = 3 if self.super_active else 1
        gained = 10 * self.combo * hoop.multiplier * mult
        self.score += gained
        self.max_combo = max(self.max_combo, self.combo)
        hoop.color = self.rng.choice(BALL_COLORS)
        n = 24 if self.super_active else 12
        for _ in range(n):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    eff_x,
                    hoop.y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    20,
                    self.ball.color,
                )
            )
        self._add_text(f"+{gained}", eff_x, hoop.y - 10, WHITE)
        if self.super_active:
            self._add_text("SWISH!", eff_x, hoop.y - 22, YELLOW)
        if self.combo >= self.SUPER_THRESHOLD:
            self.super_active = True
            self.super_timer = self.SUPER_DURATION
        self.ball.active = False
        self.respawn_timer = self.respawn_delay
        return "swish"

    def _clank(self, hoop: Hoop, eff_x: float) -> str:
        self.heat += 8
        self.combo = 0
        self.ball.vy = -self.ball.vy * 0.4
        self.ball.vx = self.ball.vx * 0.5
        self._add_text("CLANK!", eff_x, hoop.y - 10, RED)
        return "clank"

    def _rim_out(self, hoop: Hoop, eff_x: float) -> str:
        self.heat += 5
        self.ball.vy = -self.ball.vy * 0.4
        self.ball.vx = -self.ball.vx * 0.4
        self._add_text("RIM!", eff_x, hoop.y - 10, ORANGE)
        return "rim_out"

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.heat = float(self.MAX_HEAT)
            self._game_over("BENCHED")
            return
        if not self.super_active:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_effects(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    # ------------------------------------------------------------------ draw
    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_playing()

    def _center_text(self, text: str, y: int, color: int) -> None:
        pyxel.text((self.SCREEN_W - len(text) * 4) // 2, y, text, color)

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        self._center_text("SWISH CHAIN", 80, YELLOW)
        self._center_text("DRAG TO AIM  RELEASE TO SHOOT", 120, WHITE)
        self._center_text("MATCH COLOR = COMBO", 136, WHITE)
        self._center_text("4 IN A ROW = SUPER SHOT", 150, CYAN)
        self._center_text("PRESS ENTER TO START", 184, GREEN)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        self._center_text("GAME OVER", 58, RED)
        self._center_text(self.game_over_reason, 82, YELLOW)
        self._center_text(f"SCORE {self.score}", 108, WHITE)
        self._center_text(f"BEST {self.best_score}", 120, WHITE)
        self._center_text(f"MAX COMBO {self.max_combo}", 132, CYAN)
        self._center_text("PRESS R TO RETRY", 172, GREEN)

    def _draw_playing(self) -> None:
        pyxel.cls(NAVY)
        pyxel.rect(0, 222, self.SCREEN_W, self.SCREEN_H - 222, GREEN)
        pyxel.line(0, 200, self.SCREEN_W, 200, GRAY)

        for hoop in self.hoops:
            self._draw_hoop(hoop, self._hoop_eff_x(hoop))

        for tx, ty in self.trail:
            pyxel.circ(tx, ty, 1, GRAY)

        if self.super_active:
            glow = BALL_COLORS[(pyxel.frame_count // 4) % 4]
            pyxel.circ(self.ball.x, self.ball.y, 7, glow)

        ball_color = self.ball.color if self.ball.active else self.player_color
        pyxel.circ(self.ball.x, self.ball.y, 4, ball_color)

        if self.aiming:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            pvx = (self.press_x - mx) * 0.1
            pvy = (self.press_y - my) * 0.1
            pyxel.line(
                self.ball.x, self.ball.y, self.ball.x + pvx * 8, self.ball.y + pvy * 8, WHITE
            )

        pyxel.rect(120, 204, 8, 8, self.player_color)
        pyxel.text(130, 204, "YOU", WHITE)

        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        combo_color = YELLOW if self.combo >= 1 else GRAY
        pyxel.text(4, 16, f"COMBO {self.combo}", combo_color)

        pyxel.text(266, 4, "HEAT", WHITE)
        pyxel.rectb(248, 12, 64, 6, GRAY)
        heat_color = GREEN if self.heat < 50 else (YELLOW if self.heat < 80 else RED)
        fill_w = int(62 * (self.heat / self.MAX_HEAT))
        if fill_w > 0:
            pyxel.rect(249, 13, fill_w, 4, heat_color)

        factor = self.game_timer / self.GAME_TIME
        timer_color = (
            GREEN if self.game_timer > 1200 else (YELLOW if self.game_timer > 600 else RED)
        )
        pyxel.rectb(109, 7, 102, 8, GRAY)
        pyxel.rect(110, 8, int(100 * factor), 6, timer_color)

        if self.super_active:
            border_color = BALL_COLORS[(pyxel.frame_count // 4) % 4]
            pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, border_color)

        for p in self.particles:
            pyxel.pset(p.x, p.y, p.color)

        for t in self.floating_texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

    def _draw_hoop(self, hoop: Hoop, eff_x: float) -> None:
        pyxel.circb(eff_x, hoop.y, hoop.radius, hoop.color)
        pyxel.tri(
            eff_x - hoop.radius,
            hoop.y,
            eff_x + hoop.radius,
            hoop.y,
            eff_x,
            hoop.y + hoop.radius + 12,
            WHITE,
        )
        pyxel.text(int(eff_x) - 2, hoop.y - hoop.radius - 12, f"{hoop.multiplier}x", hoop.color)


if __name__ == "__main__":
    Game()
